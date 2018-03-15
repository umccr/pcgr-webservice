import os
import logging
from shelljob import proc

from flask import Flask, jsonify

# DataDog APM metrics tracing
#from ddtrace import tracer
#from ddtrace.contrib.flask import TraceMiddleware
#traced_app = TraceMiddleware(app, tracer, service="pcgr-webservice", distributed_tracing=True)

# Initialise the logger
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def create_app():

    # instantiate the app
    app = Flask(__name__)

    # set config
    app_settings = os.getenv('APP_SETTINGS')
    app.config.from_object(app_settings)

    # register blueprints
    from server.api.views import pcgr_api
    app.register_blueprint(pcgr_api)

    return app


# Aux functions
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

