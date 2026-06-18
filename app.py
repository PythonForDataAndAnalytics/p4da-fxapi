# p4da fx web api (supports v1, v2, and v3 endpoints)

import os
from flask import Flask, jsonify, request
from usage import increment_request_count, write_usage_activity_today
from QueryRates import QueryRates

app = Flask(__name__)

# TODO:
# /fxapi/v2/rates - without <ccyfrom>/<ccyto>


DBFILENAME = os.path.join('data', 'fxdata.db') # dir and filename of fx sqlite database

# track requests, and limit number per day from a given device
@app.before_request
def check_request_limit():
    # Check if the request limit has been reached for this user
    print('*** Starting check_request_limit ***')
    print('request.endpoint:', request.endpoint)
    #if request.endpoint != None and request.endpoint.endswith('save_usage_today'):
    #    return
    if not increment_request_count():
        return jsonify({"error": "Request limit exceeded for today"}), 429

# Endpoint to manually save today's usage activity to 'usage_today.csv' without clearing it
@app.route('/fxapi/v3/save_usage_today')
def save_usage_today():
    write_usage_activity_today()  # Save the current usage activity to the file
    return jsonify({'status': 'Usage activity saved to usage_today.csv'}), 200

# thin wrapper function to get currency rates
# including support for query params: asoftime ; source
def getrates(ccyfrom, ccyto, args):
    queryRates = QueryRates(DBFILENAME)
    d = {}
    d['ccyfrom'] = ccyfrom
    d['ccyto'] = ccyto
    if 'asoftime' in args: d['asoftime'] = args['asoftime']
    if 'source' in args: d['source'] = args['source']
    rates = queryRates.query(d)
    return rates

# version 3 - return metadata & data
@app.route('/fxapi/v3/rates/<ccyfrom>/<ccyto>', methods=['GET'])
def get_currency_ratev3(ccyfrom, ccyto):
    print('get_currency_ratev3', ccyfrom, ccyto)
    
    # Print all query parameters for debugging purposes
    print("=== QUERY PARAMETERS:")
    for k, v in request.args.items():
        print(k, v, sep='=')
    print(('=== END QUERY PARAMETERS'))

    result = getrates(ccyfrom, ccyto, request.args)

    # handle error/empty cases
    if 'error' in result:
        return jsonify({'error':result['error']}), result['error_code']
    if len(result) == 0:
        return jsonify({"error": "No results found"}), 404

    return jsonify(result)

# version 2: support multiple ccys, but do not return metadata
@app.route('/fxapi/v2/rates/<ccyfrom>/<ccyto>', methods=['GET'])
def get_currency_ratev2(ccyfrom, ccyto):
    print('get_currency_ratev2', ccyfrom, ccyto)
    
    # Print all query parameters for debugging purposes
    # TODO: decide if query params are supported in V2
    print("=== QUERY PARAMETERS:")
    for k, v in request.args.items():
        print(k, v, sep='=')
    print(('=== END QUERY PARAMETERS'))

    result = getrates(ccyfrom, ccyto, request.args) 

    if 'error' in result:
        return jsonify({'error':result['error']}), result['error_code']
    # extract and return result (rates only, no metadata)
    if len(result) == 0:
        return jsonify({"error": "No results found"}), 404
    
    # v2 excludes metadata
    rates = result['data']
    if len(rates) == 0:
        return jsonify({"error": "No results found"}), 404
    return jsonify(rates)

# version 1: one ccy pair, for the latest date and default source
@app.route('/fxapi/v1/rates/<ccyfrom>/<ccyto>', methods=['GET'])
def get_currency_ratev1(ccyfrom, ccyto):
    print('get_currency_ratev1', ccyfrom, ccyto)

    # for V1, multi-ccy not allowed
    if ccyto == '*':
        return jsonify({"error": 'ccyto must be specified'}), 400

    # make the call to get the rate
    args = { } # V1 - query parameters not supported in V1 api
    result = getrates(ccyfrom, ccyto, args)

    # handle error/empty cases
    if 'error' in result:
        return jsonify({'error':result['error']}), result['error_code']
    if len(result) == 0:
        return jsonify({"error": "No results found"}), 404


    # v1 excludes metdata; just includes a single rate
    rates = result['data']
    print(rates)
    if len(rates) == 0:
        return jsonify({"error": "No results found"}), 404
    rate = rates[ccyto]
    finalresult = {'rate': rate}
    return jsonify(finalresult)

# version 3 - return asoftime earliest/latest span for a given source
@app.route('/fxapi/v3/times', methods=['GET'])
def get_time_span():
    print('get_time_span')
    
    queryRates = QueryRates(DBFILENAME)

    # get the source id
    if 'source' not in request.args.keys():
        print('*** "source" not found in query parameters')
        return jsonify({"error": "Source must be specified"}), 400
    source = request.args['source']
    sourceid = queryRates.querySourceID(source)
    if sourceid == None:
        print(f'*** source of "{source}" not found in data')
        return jsonify({"error": "Source not found"}), 404

    result = queryRates.queryTimeSpan(sourceid)

    # handle error/empty cases
    if 'error' in result:
        return jsonify({'error':result['error']}), result['error_code']
    if len(result) == 0:
        return jsonify({"error": "No results found"}), 404

    return jsonify(result)

# version 3 - return list of sources
@app.route('/fxapi/v3/sources', methods=['GET'])
def get_sources():
    print('get_sources')
    
    queryRates = QueryRates(DBFILENAME)
    result = queryRates.querySources()

    # handle error/empty cases
    if 'error' in result:
        return jsonify({'error':result['error']}), result['error_code']
    if len(result) == 0:
        return jsonify({"error": "No results found"}), 404

    return jsonify(result)


# To run the Flask app
if __name__ == '__main__':
    app.run(debug=True)
