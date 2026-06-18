# validation and access for FX rates for SQLite database (w/ tables: sources, snapshots, rates)
import sqlite3 as db
from datetime import datetime
from collections import OrderedDict

# TODO: check valid ccys

class QueryRates:
    def __init__(self, filename):
        self.filename = filename
        self.sourceid = 1 # default source id

    # input: dictionary w/ 'fromccy', optionally: 'toccy', 'asoftime', 'source'
    def query(self, d):
        print('QueryRates.query', d)

        # if the source name is in d - find its id, otherwise use default
        if 'source' in d:
            sourceid = self.querySourceID(d['source'])
            if sourceid == None: # no source wth that name
                return {'error':'No source with name '+d['source'], 'error_code':404}
            sourcename = d['source']
        else:
            sourceid = self.sourceid
            sourcename = self.querySourceName(sourceid)

        # determine the datetime from the asoftime
        if 'asoftime' in d:
            asoftime = d['asoftime']
            if not QueryRates.is_valid_datetime(asoftime):
                return {'error':'Invalid asoftime format', 'error_code':400}
        else:
            asoftime = '2099-01-01'
        datetime = self.queryLatestFromAsoftime(sourceid, asoftime)
        print(f'*** asoftime={asoftime} datetime={datetime}')
        if datetime == None:
            return {'error':'No data on/before asoftime', 'error_code':404}

        # check the ccys
        if not self.checkccy(d['ccyfrom'], 'ccyfrom'):
            return {'error':'No data for from ccy '+d['ccyfrom'], 'error_code':404}
        ccyto = d['ccyto']
        if ccyto != '*' and not self.checkccy(d['ccyto'], 'ccyto'):
            return {'error':'No data for to ccy '+d['ccyto'], 'error_code':404}

        # check the timestamp format
        # TODO: adjust based on above new code for datetime
        #if 'asoftime' in d:
        #    ts = d['asoftime']
        #    if not QueryRates.is_valid_datetime(ts):
        #        return {'error':'Invalid asoftime format', 'error_code':400}

        # get the rates for sourceid and datetime
        rates = self.queryRates(d, sourceid, datetime)

        # form meta/data results and return
        # TODO: distinguish asoftime from datetime
        metadata = {'asoftime':datetime, 'source':sourcename}
        result = {'metadata':metadata, 'data':rates}
        #result = OrderedDict()
        #result['metadata'] = metadata
        #result['data'] = rates
        return result

    # for a given soureid, datetime, d['ccyfrom'], and optionally d['ccyto'], find/return rate(s)
    def queryRates(self, d, sourceid, datetime):
        print('QueryRates.queryRates', d, sourceid, datetime)
        connection = db.connect(self.filename)
        sql = "SELECT ccyto, rate FROM rates \n" +\
              "WHERE sourceid = " + str(sourceid) +'\n'+\
              "AND datetime = '" + datetime +"'\n"+\
              "AND ccyfrom = '" + d['ccyfrom'] +"'\n"
        if 'ccyto' in d and d['ccyto'] != '*':
            sql += "AND ccyto = '" + d['ccyto'] +"'\n"
        sql += "ORDER BY ccyto;"
        print(sql)
        cursor = connection.cursor()
        cursor.execute(sql)
        result = {} # dictionary of toccy:rate pairs
        for row in cursor:
            #print(row)
            ccyto = row[0]
            rate = row[1]
            if d['ccyfrom'] != ccyto:
                result[ccyto] = rate
        cursor.close()
        connection.close()
        #print(result)
        return result

    # check if a ccy code is in any of the data (for given field name - either 'ccyfrom' or 'ccyto'); return True/False
    def checkccy(self, ccy, ccyfield):
        connection = db.connect(self.filename)
        cursor = connection.cursor()
        sql = "SELECT DISTINCT ccyfrom FROM rates WHERE " + ccyfield + " = '" + ccy + "';"
        print(sql)
        cursor.execute(sql)
        result = False
        for row in cursor:
            result = True
        cursor.close()
        connection.close()
        return result

    # get source id for a given source name
    def querySourceID(self, source):
        connection = db.connect(self.filename)
        cursor = connection.cursor()
        sql = "SELECT id FROM sources WHERE lower(name) = '" + source.lower() + "';" 
        print(sql)
        cursor.execute(sql)
        result = None
        for row in cursor:
            result = row[0]
        cursor.close()
        connection.close()
        return result

    # get source name for a given source ID
    def querySourceName(self, sourceid):
        connection = db.connect(self.filename)
        cursor = connection.cursor()
        sql = "SELECT name FROM sources WHERE id = " + str(sourceid)
        print(sql)
        cursor.execute(sql)
        result = None
        for row in cursor:
            result = row[0]
        cursor.close()
        connection.close()
        return result

    # get latest datetime for a given source on/before a given asoftime
    def queryLatestFromAsoftime(self, sourceid, asoftime):
        connection = db.connect(self.filename)
        cursor = connection.cursor()
        sql = "SELECT max(datetime) FROM rates WHERE sourceid = " + str(sourceid) + " AND datetime <= '" + asoftime +"';"
        print(sql)
        cursor.execute(sql)
        result = None
        for row in cursor:
            result = row[0]
        cursor.close()
        connection.close()
        return result

    # check if a ISO8601 date/time is valid, allowing for optional T and optional seconds
    @staticmethod
    def is_valid_datetime(datetime_str):
    # Define possible formats with optional T and optional seconds
        formats = [
            "%Y-%m-%dT%H:%M:%S",  # With T and seconds
            "%Y-%m-%d %H:%M:%S",  # With space and seconds
            "%Y-%m-%dT%H:%M",     # With T, without seconds
            "%Y-%m-%d %H:%M",     # With space, without seconds
            "%Y-%m-%d"            # date only
        ]
        for fmt in formats:
            try:
                datetime.strptime(datetime_str, fmt)
                return True
            except ValueError:
                continue
        return False

    # return the start/end times of the rates data, for a given sourceid
    def queryTimeSpan(self, sourceid):
        connection = db.connect(self.filename)
        cursor = connection.cursor()
        sql = "SELECT min(datetime), max(datetime) FROM rates"
        sql += " WHERE sourceid = " + str(sourceid) + ';' 
        print(sql)
        cursor.execute(sql)
        times = None
        for row in cursor:
            times = row[0], row[1]
        cursor.close()
        connection.close()
        if times == None:
            result = {'error': 'No data found', 'error_code': 404}
        else:
            result = {'times': times}
        return result

    # return the list of sources
    def querySources(self):
        connection = db.connect(self.filename)
        cursor = connection.cursor()
        sql = "SELECT name FROM sources;" 
        print(sql)
        cursor.execute(sql)
        sources = []
        for row in cursor:
            sources.append(row[0])
        cursor.close()
        connection.close()
        if len(sources) == 0:
            result = {'error': 'No data found', 'error_code': 404}
        else:
            result = {'sources': sources}
        return result


# test QueryRates methods for validation and retrieval
if __name__ == '__main__':
    queryRates = QueryRates('data/fxdata.db')
    asoftime = '2024-06-30T12:00'
    d = {'ccyfrom': 'USD', 'ccyto':'*', 'asoftime':asoftime}
    #d = {'ccyfrom': 'USD', 'ccyto':'*'}
    d['source'] = 'usgov-H10'
    rates = queryRates.query(d)
    print(rates)

    any = queryRates.checkccy('USD', 'ccyfrom')
    print('valid ccy:', any)

    print('valid ts:', QueryRates.is_valid_datetime(asoftime))

    # deprecated
    #any = queryRates.checkts(asoftime)
    #print(any)

    sourceid = queryRates.querySourceID('usgov-H10')
    print('sourceid:', sourceid)

    times = queryRates.queryTimeSpan(sourceid)
    print(times)

    sources = queryRates.querySources()
    print(sources)