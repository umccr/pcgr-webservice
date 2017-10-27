Personal Cancer Genome Reporter Web Service
===========================================

Barebones work in process to wrap PCGR as a webservice. Upload files and run batched analysis on a [pre-deployed PCGR instance](http://github.com/umccr/pcgr-deploy).

To put it simply:

    curl -X POST -F 'file=@foo.vcf' http://ec2instance/upload
    curl http://ec2instance/pcgr/run

pcgr-webservice is just a small Flask scaffold that can be used as an example to build other [(minimal?) webservices](https://testdriven.io/part-one-intro/).
