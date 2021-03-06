from requests import Request, Session
import httplib
import md5

# LEGACY FORMAT

s = Session()
url = "http://0.0.0.0:6543/gps_update"
# params = '1,20141022150735,42.234375,-8.716689,100,2.060000,85'
params = 'sendDataPacket: 12345678910,,0.000000,20140722011302,42.326602,100,0.000000,0.000000,-7.818424,10,0.000000'
req = Request('POST', url, data=params)
prepped = req.prepare()
# prepped.headers['Content-MD5'] = md5.new(prepped.body).hexdigest()
r = s.send(prepped)
print str(r._content)
"""#params = '1,20141023150735,0.000462773316983889,-8.45045187771234e-07,100,2.060000,5' + '|||' +\
#    '2,20141022150735,0.000462562123057176,-4.88863177617844e-07,100,2.060000,50';
params = 'sendDataPacket: 2,,1.21,20141022150735,42.234375,60,0.21,5.65,-8.716689,100,21.39' + '|||' +\
    '2,,1.21,20141122150735,0.000462562123057176,60,0.21,5.65,-4.88863177617844e-07,100,21.39'
req = Request('POST', url, data=params)
prepped = req.prepare()
# prepped.headers['Content-MD5'] = md5.new(prepped.body).hexdigest()
r = s.send(prepped)
print str(r._content)
"""

# NEW FORMAT

s = Session()
url = "http://0.0.0.0:6543/gps_update"
# params = '1,20141022150735,42.234375,-8.716689,100,2.060000,85'
params = 'data: 12345678910|20140722011302,10,42.326602,-7.818424,0.000000,0.000000,0.000000,0.000000,0'
req = Request('POST', url, data=params)
prepped = req.prepare()
# prepped.headers['Content-MD5'] = md5.new(prepped.body).hexdigest()
r = s.send(prepped)
print str(r._content)