import os
import glob
import boto3

from server import create_app, mkdir_out, allowed_file, preprocess_vcf
from shelljob import proc

from flask import Blueprint, Response, request, redirect, url_for, jsonify, flash
from werkzeug.utils import secure_filename

import logging

app = create_app()
s3 = boto3.client('s3')

# Initialise the logger
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

pcgr_api = Blueprint('pcgr', __name__)


@pcgr_api.route('/ping', methods=['GET'])
def ping_pong():
    return jsonify({
        'status': 'success',
        'message': 'pong!'
    })

@pcgr_api.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('upload_file',
                                    filename=filename))
    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form method=post enctype=multipart/form-data>
      <p><input type=file name=file>
         <input type=submit value=Upload>
    </form>
    '''

@pcgr_api.route('/pcgr/run', methods=['GET'])
def run_pcgr():
    vcfs_to_process = glob.glob(os.path.join(app.config['UPLOAD_FOLDER'], '*.gz'))
    log.info("VCFs to be processed: {}".format(vcfs_to_process))
    
    g = proc.Group()
    
    def _read_process():
        while g.is_pending():
           lines = g.readlines()
           for proc, line in lines:
              yield line

    for vcf in vcfs_to_process:
        # might be useful for dind (docker in docker)
        # https://github.com/jpetazzo/dind
        # cmd = ['/usr/bin/python', 'pcgr/pcgr.py', '--input_vcf', os.path.abspath(vcf), '--msig_identify', '--list_noncoding', 'pcgr', 'report', 'output'] 
        preprocess_vcf(vcf)
        output_dir = mkdir_out(vcf)

        cmd = ['/usr/bin/python', '/mnt/work/pcgr/pcgr.py', '--force_overwrite', '--input_vcf', os.path.abspath(vcf), '--msig_identify', '--list_noncoding', '/mnt/work/pcgr', output_dir, output_dir]
        log.info("Running: {}".format(cmd))
        g.run(cmd)
        log.info("Finished: {}".format(output_dir))
        log.info("Uploading: {}".format(output_dir))

        s3.meta.client.upload_file(output_dir, 'umccr-pcgr')
        log.info("Results uploaded")

    return Response( _read_process(), mimetype= 'text/plain' )