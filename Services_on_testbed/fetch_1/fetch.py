#This code is developed based on the code in project BookInfo

from __future__ import print_function
from flask_bootstrap import Bootstrap
from flask import _request_ctx_stack as stack
from jaeger_client import Tracer, ConstSampler
from jaeger_client.reporter import NullReporter
from jaeger_client.codecs import B3Codec
from opentracing.ext import tags
from opentracing.propagation import Format
from opentracing_instrumentation.request_context import span_in_context
from json2html import *
import logging
import os
from flask import Flask
from flask import jsonify
from flask_pymongo import PyMongo
import time
import random


try:
    import http.client as http_client
except ImportError:
    # Python 2
    import httplib as http_client
http_client.HTTPConnection.debuglevel = 1

app = Flask(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True
app.logger.addHandler(logging.StreamHandler(sys.stdout))
app.logger.setLevel(logging.DEBUG)

# Set the secret key to some random bytes. Keep this really secret!
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

Bootstrap(app)

servicesDomain = "" if (os.environ.get("SERVICES_DOMAIN") is None) else "." + os.environ.get("SERVICES_DOMAIN")
reviewsHostname = "newfetch" if (os.environ.get("FETCH_HOSTNAME") is None) else os.environ.get("FETCH_HOSTNAME")
mongoURL = 'mongodb://10.68.116.136:30051/admin' if (os.environ.get("MONGO_DB_URL") is None) else os.environ.get("MONGO_DB_URL")

flood_factor = 0 if (os.environ.get("FLOOD_FACTOR") is None) else int(os.environ.get("FLOOD_FACTOR"))

fetch = {
    "name": "http://{0}{1}:9090".format(reviewsHostname, servicesDomain),
    "endpoint": "newfetch",
    "children": []
}

service_dict = {
    "newfetch": fetch,
}

app.config['MONGO_DBNAME'] = 'admin'
app.config['MONGO_URI'] = mongoURL
print(mongoURL)

mongo = PyMongo(app)

tracer = Tracer(
    one_span_per_rpc=True,
    service_name='newfetch',
    reporter=NullReporter(),
    sampler=ConstSampler(decision=True),
    extra_codecs={Format.HTTP_HEADERS: B3Codec()}
)

def trace():
    '''
    Function decorator that creates opentracing span from incoming b3 headers
    '''
    def decorator(f):
        def wrapper(*args, **kwargs):
            request = stack.top.request
            try:
                # Create a new span context, reading in values (traceid,
                # spanid, etc) from the incoming x-b3-*** headers.
                span_ctx = tracer.extract(
                    Format.HTTP_HEADERS,
                    dict(request.headers)
                )
                # Note: this tag means that the span will *not* be
                # a child span. It will use the incoming traceid and
                # spanid. We do this to propagate the headers verbatim.
                rpc_tag = {tags.SPAN_KIND: tags.SPAN_KIND_RPC_SERVER}
                span = tracer.start_span(
                    operation_name='op', child_of=span_ctx, tags=rpc_tag
                )
            except Exception as e:
                # We failed to create a context, possibly due to no
                # incoming x-b3-*** headers. Start a fresh span.
                # Note: This is a fallback only, and will create fresh headers,
                # not propagate headers.
                span = tracer.start_span('op')
            with span_in_context(span):
                r = f(*args, **kwargs)
                return r
        wrapper.__name__ = f.__name__
        return wrapper
    return decorator

# The UI:
@app.route('/newfetch/books/<points>')
def fetch(points):
    city = mongo.db.books
    print("_id:", points)
    s = city.find_one({"_id": int(points)})
    print(s)
    if s:
        output = str(s) + "(fetch3)"
    else:
        output = "No such book (fetch3)"
    response = jsonify(output)
    response.headers.set("Content-Type", "application/json")
    return response

@app.route('/newfetch/city/<points>')
def fetch_city(points):
    city = mongo.db.city
    print("certificate_number:", points)
    s = city.find_one({"certificate_number": int(points)})
    print(s)
    if s:
        output = str(s) + "(fetch3)"
    else:
        output = "No such city (fetch3)"
    response = jsonify(output)
    response.headers.set("Content-Type", "application/json")
    return response

@app.route('/health')
def health():
    return 'Product page is healthy'

class Writer(object):
    def __init__(self, filename):
        self.file = open(filename, 'w')

    def write(self, data):
        self.file.write(data)

    def flush(self):
        self.file.flush()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        logging.error("usage: %s port" % (sys.argv[0]))
        sys.exit(-1)

    p = int(sys.argv[1])
    logging.info("start at port %s" % (p))
    # Python does not work on an IPv6 only host
    # https://bugs.python.org/issue10414
    app.run(host='0.0.0.0', port=p, debug=True, threaded=True)
