import CGIHTTPServer

import BaseHTTPServer

class Handler(CGIHTTPServer.CGIHTTPRequestHandler):

    cgi_directories = ["/cgi"]

PORT = 8001

httpd = BaseHTTPServer.HTTPServer(("", PORT), Handler)

print "serving at port", PORT

httpd.serve_forever()