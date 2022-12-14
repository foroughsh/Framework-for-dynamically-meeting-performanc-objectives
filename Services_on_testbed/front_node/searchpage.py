#This code is developed based on the code presented for BookInfo code.

from __future__ import print_function
from flask_bootstrap import Bootstrap
from flask import Flask, request, session, render_template, redirect, url_for, abort
from flask import _request_ctx_stack as stack
from jaeger_client import Tracer, ConstSampler
from jaeger_client.reporter import NullReporter
from jaeger_client.codecs import B3Codec
from opentracing.ext import tags
from opentracing.propagation import Format
from opentracing_instrumentation.request_context import get_current_span, span_in_context
import simplejson as json
import requests
import sys
from json2html import *
import logging
import requests
import os
import asyncio
import random
import time

# These two lines enable debugging at httplib level (requests->urllib3->http.client)
# You will see the REQUEST, including HEADERS and DATA, and RESPONSE with HEADERS but without DATA.
# The only thing missing will be the response.body which is not logged.
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
fetchHostname = "newfetch" if (os.environ.get("FETCH_HOSTNAME") is None) else os.environ.get("FETCH_HOSTNAME")

flood_factor = 0 if (os.environ.get("FLOOD_FACTOR") is None) else int(os.environ.get("FLOOD_FACTOR"))

fetch = {
    "name": "http://{0}{1}:9090".format(fetchHostname, servicesDomain),
    "endpoint": "newfetch",
    "children": []
}

searchpage = {
    "name": "http://{0}{1}:9090".format(fetchHostname, servicesDomain),
    "endpoint": "newfetch",
    "children": [fetch]
}

service_dict = {
    "newsearchpage": searchpage,
    "newfetch": fetch,
}

city_rate_limit = {
    "counter" : 0,
    "stamp" : time.time(),
    "threshold" : 5
}

books_rate_limit = {
    "counter" : 0,
    "stamp" : time.time(),
    "threshold" : 5
}


# A note on distributed tracing:
#
# Although Istio proxies are able to automatically send spans, they need some
# hints to tie together the entire trace. Applications need to propagate the
# appropriate HTTP headers so that when the proxies send span information, the
# spans can be correlated correctly into a single trace.
#
# To do this, an application needs to collect and propagate headers from the
# incoming request to any outgoing requests. The choice of headers to propagate
# is determined by the trace configuration used. See getForwardHeaders for
# the different header options.
#
# This example code uses OpenTracing (http://opentracing.io/) to propagate
# the 'b3' (zipkin) headers. Using OpenTracing for this is not a requirement.
# Using OpenTracing allows you to add application-specific tracing later on,
# but you can just manually forward the headers if you prefer.
#
# The OpenTracing example here is very basic. It only forwards headers. It is
# intended as a reference to help people get started, eg how to create spans,
# extract/inject context, etc.

# A very basic OpenTracing tracer (with null reporter)
tracer = Tracer(
    one_span_per_rpc=True,
    service_name='newsearchpage',
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

def getForwardHeaders(request):
    headers = {}

    # x-b3-*** headers can be populated using the opentracing span
    span = get_current_span()
    carrier = {}
    tracer.inject(
        span_context=span.context,
        format=Format.HTTP_HEADERS,
        carrier=carrier)

    headers.update(carrier)

    # We handle other (non x-b3-***) headers manually
    if 'user' in session:
        headers['end-user'] = session['user']

    # Keep this in sync with the headers in details and reviews.
    incoming_headers = [
        # All applications should propagate x-request-id. This header is
        # included in access log statements and is used for consistent trace
        # sampling and log sampling decisions in Istio.
        'x-request-id',

        # Lightstep tracing header. Propagate this if you use lightstep tracing
        # in Istio (see
        # https://istio.io/latest/docs/tasks/observability/distributed-tracing/lightstep/)
        # Note: this should probably be changed to use B3 or W3C TRACE_CONTEXT.
        # Lightstep recommends using B3 or TRACE_CONTEXT and most application
        # libraries from lightstep do not support x-ot-span-context.
        'x-ot-span-context',

        # Datadog tracing header. Propagate these headers if you use Datadog
        # tracing.
        'x-datadog-trace-id',
        'x-datadog-parent-id',
        'x-datadog-sampling-priority',

        # W3C Trace Context. Compatible with OpenCensusAgent and Stackdriver Istio
        # configurations.
        'traceparent',
        'tracestate',

        # Cloud trace context. Compatible with OpenCensusAgent and Stackdriver Istio
        # configurations.
        'x-cloud-trace-context',

        # Grpc binary trace context. Compatible with OpenCensusAgent nad
        # Stackdriver Istio configurations.
        'grpc-trace-bin',

        # b3 trace headers. Compatible with Zipkin, OpenCensusAgent, and
        # Stackdriver Istio configurations. Commented out since they are
        # propagated by the OpenTracing tracer above.
        # 'x-b3-traceid',
        # 'x-b3-spanid',
        # 'x-b3-parentspanid',
        # 'x-b3-sampled',
        # 'x-b3-flags',

        # Application-specific headers to forward.
        'user-agent',
    ]
    # For Zipkin, always propagate b3 headers.
    # For Lightstep, always propagate the x-ot-span-context header.
    # For Datadog, propagate the corresponding datadog headers.
    # For OpenCensusAgent and Stackdriver configurations, you can choose any
    # set of compatible headers to propagate within your application. For
    # example, you can propagate b3 headers or W3C trace context headers with
    # the same result. This can also allow you to translate between context
    # propagation mechanisms between different applications.

    for ihdr in incoming_headers:
        val = request.headers.get(ihdr)
        if val is not None:
            headers[ihdr] = val

    return headers

@app.route('/login', methods=['POST'])
def login():
    user = request.values.get('username')
    response = app.make_response(redirect(request.referrer))
    session['user'] = user
    return response


@app.route('/logout', methods=['GET'])
def logout():
    response = app.make_response(redirect(request.referrer))
    session.pop('user', None)
    return response


# The UI:
@app.route('/')
@app.route('/index.html')
def index():
    """ Display productpage with normal user and test user buttons"""
    global searchpage

    table = json2html.convert(json=json.dumps(searchpage),
                              table_attributes="class=\"table table-condensed table-bordered table-hover\"")

    return render_template('index.html', serviceTable=table)


@app.route('/health')
def health():
    return 'Product page is healthy'

@app.route('/api/v1/')
def Forough():
    return 'I Love U Forough :*'

@app.route('/books')
@trace()
def front_books():

    global books_rate_limit

    rate_limit_stamp = time.time()

    if (rate_limit_stamp % 1 == 0) or (rate_limit_stamp - books_rate_limit["stamp"] > 1):
        books_rate_limit["counter"] = 0
        books_rate_limit["stamp"] = rate_limit_stamp

    if (books_rate_limit["counter"] > books_rate_limit["threshold"]):
        abort(429)
    books_rate_limit["counter"] += 1

    product_id = random.randint(1, 800)
    headers = getForwardHeaders(request)
    user = session.get('user', '')
    product = getFetch(product_id)
    fetchStatus, fetch = getFetchedPoints_books(product_id,headers)
    return render_template(
        'searchpage.html',
        # detailsStatus=detailsStatus,
        fetchStatus=fetchStatus,
        product=product,
        # details=details,
        fetch=fetch,
        user=user)

@app.route('/city')
@trace()
def front_city():

    global city_rate_limit

    rate_limit_stamp = time.time()

    if (rate_limit_stamp % 1 == 0) or (rate_limit_stamp - city_rate_limit["stamp"]>1):
        city_rate_limit["counter"] = 0
        city_rate_limit["stamp"] = rate_limit_stamp

    if (city_rate_limit["counter"] > city_rate_limit["threshold"]):
        abort(429)
    city_rate_limit["counter"] += 1
    product_id = random.randint(1000000,10000000)
    headers = getForwardHeaders(request)
    user = session.get('user', '')
    product = getFetch(product_id)
    fetchStatus, fetch = getFetchedPoints_city(product_id,headers)
    return render_template(
        'searchpage.html',
        fetchStatus=fetchStatus,
        product=product,
        fetch=fetch,
        user=user)


def getFetch(product_id):
    products = getProducts()
    if product_id + 1 > len(products):
        return None
    else:
        return products[product_id]

# The API:
@app.route('/api/v1/search')
def searchapi():
    return json.dumps(getProducts()), 200, {'Content-Type': 'application/json'}


@app.route('/api/v1/newfetch/books/<points>')
@trace()
def fetchapi_book(points):
    headers = getForwardHeaders(request)
    status, fetches = getFetchedPoints_books(points, headers)
    return json.dumps(fetches), status, {'Content-Type': 'application/json'}

@app.route('/api/v1/newfetch/city/<points>')
@trace()
def fetchapi_city(points):
    headers = getForwardHeaders(request)
    status, fetches = getFetchedPoints_city(points, headers)
    return json.dumps(fetches), status, {'Content-Type': 'application/json'}

@app.route('/ratecity/<ratelimitc>')
@trace()
def rate_city(ratelimitc):
    city_rate_limit["threshold"] = int(float(ratelimitc))
    statecode = 200
    status = 200
    return json.dumps(ratelimitc), status, {'Content-Type': 'application/json'}

@app.route('/ratebook/<ratelimitb>')
@trace()
def rate_books(ratelimitb):
    books_rate_limit["threshold"] = int(float(ratelimitb))
    statecode = 200
    status = 200
    return json.dumps(ratelimitb), status, {'Content-Type': 'application/json'}

# Data providers:
def getProducts():
    return [
        {
            'points': 123
        }
    ]

def getFetchedPoints_books(fetchpoints, headers):
    for _ in range(1):
        try:
            url = fetch['name'] + "/" + fetch['endpoint'] + "/books/" + str(fetchpoints)
            res = requests.get(url, headers=headers, timeout=20.0)
        except BaseException:
            res = None
        if res and res.status_code == 200:
            return 200, res.json()
    status = res.status_code if res is not None and res.status_code else 500
    return status, {'error': 'Sorry, the information for this book is not available.'}

def getFetchedPoints_city(fetchpoints, headers):

    for _ in range(1):
        try:
            url = fetch['name'] + "/" + fetch['endpoint'] + "/city/" + str(fetchpoints)
            res = requests.get(url, headers=headers, timeout=20.0)
        except BaseException:
            res = None
        if res and res.status_code == 200:
            return 200, res.json()
    status = res.status_code if res is not None and res.status_code else 500
    return status, {'error': 'Sorry, the information for this city is not available.'}


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
