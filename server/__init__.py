import os
import glob
import logging
from shelljob import proc
from flask import Flask, Response, request, redirect, url_for, jsonify
from werkzeug import secure_filename

# DataDog APM metrics tracing
#from ddtrace import tracer
#from ddtrace.contrib.flask import TraceMiddleware

# Initialise the logger
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


# instantiate the app
app = Flask(__name__)

# set config
app_settings = os.getenv('APP_SETTINGS')
app.config.from_object(app_settings)

#traced_app = TraceMiddleware(app, tracer, service="pcgr-webservice", distributed_tracing=True)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def mkdir_out(vcf):
    """ PCGR does not automatically create output directories. Since we are iterating over the samples,
        create one output dir per sample
    """
    output_dir = "output-{vcf}".format(vcf=os.path.basename(vcf))
    os.makedirs(output_dir)
    return output_dir

def preprocess_vcf(vcf):
    """ Make sure the input VCF is compressed with bgzf and indexed with tabix
    """
    cmd = []
    g = proc.Group()
    
    def _read_process():
        while g.is_pending():
           lines = g.readlines()
           for proc, line in lines:
              yield line

    # does it quack like a vcf?
    if not 'vcf' in vcf:
        raise ValueError('The file {filename} does not seem to be a VCF file'.format(filename=vcf))

    # uncompressed vcf
    if os.path.splitext(vcf)[-1] != '.gz':
        cmd = ['bgzip', vcf, '&& ']

    cmd += ['tabix', os.path.abspath(vcf)]
    log.info("Running: {}".format(cmd))
    g.run(cmd)

    return Response( _read_process(), mimetype= 'text/plain' )


@app.route('/ping', methods=['GET'])
def ping_pong():
    return jsonify({
        'status': 'success',
        'message': 'pong!'
    })

@app.route('/', methods=['GET', 'POST'])
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

@app.route('/pcgr/run', methods=['GET'])
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

    return Response( _read_process(), mimetype= 'text/plain' )
