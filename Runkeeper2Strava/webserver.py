import http.server as hs
from urllib.parse import urlparse

args = None


class RequestHandler(hs.BaseHTTPRequestHandler):

    def do_GET(self):
        global args

        parsed_url = urlparse(self.path)
        args = parsed_url.query

        self.send_response(200)
        self.end_headers()
        self.wfile.write("<h3>You can now close this tab return to the app</h3>".encode())

    def log_message(self, format, *args):
        pass


def run(port: int, handler_class=RequestHandler):
    server_address = ('', port)
    httpd = hs.HTTPServer(server_address, handler_class)
    httpd.handle_request()


def get_auth(port):
    global args

    run(int(port))

    process_args = args

    args = None

    process_args = process_args.split("&")
    output_args = {}

    for arg in process_args:
        a_sp = arg.split("=")
        output_args[a_sp[0]] = a_sp[1]

    return output_args
