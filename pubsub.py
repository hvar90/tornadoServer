#!/usr/bin/env python
import logging
import tornado.ioloop
import tornado.options
import tornado.web
import json
import os
from tornado.options import define, options

define("port", default=5000, help="run on the given port", type=int)


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        try:
            json.dumps(MessageMixin.cache)
        except KeyError:
            raise tornado.web.HTTPError(404)
            



class MessageMixin(object):
    waiters = {}
    cache = {}
    cache_size = 200

    def wait_for_messages(self, callback, cursor=None):
        t = self.section_slug
        cache = self.cache.setdefault(t, [])
        waiters = self.waiters.setdefault(t, [])
        if cursor:
            index = 0
            for i in xrange(len(cache)):
                index = len(cache) - i - 1
                if cache[index]["id"] == cursor:
                    break
            recent = cache[index + 1:]
            if recent:
                callback(recent)
                return None
        waiters.append(callback)

    def new_messages(self, posts,idThread,isOpPost):
        t = self.section_slug
        cache = self.cache.setdefault(t, [])
        #print t
        #print self.waiters.setdefault(t, [])
        waiters = self.waiters.setdefault(t, [])

        for callback in waiters:
            try:
                callback(posts,idThread,isOpPost)
            except Exception:
                logging.error("Error in waiter callback", exc_info=True)
        waiters = []
        cache.extend(posts)
        if len(cache) > self.cache_size:
            cache = cache[-self.cache_size:]


class MessageNewHandler(MainHandler, MessageMixin):
    def post(self, section_slug):
        self.section_slug = section_slug
        post = self.get_argument("html")
        idThread = self.get_argument("idThread")
        isOpPost = self.get_argument("isOpPost")
        redirect_to = self.get_argument("next", None)
        if redirect_to:
            self.redirect(redirect_to)
        else:
            self.write(post)
        self.new_messages([post],idThread,isOpPost)


class MessageUpdatesHandler(MainHandler, MessageMixin):
    @tornado.web.asynchronous
    def post(self, section_slug):
        self.section_slug = section_slug
        try:
            self.wait_for_messages(self.on_new_messages,
                                   cursor=self.get_argument("cursor", None))
        except KeyError:
            raise tornado.web.HTTPError(404)

    def on_new_messages(self, posts,idThread,isOpPost):
        # Closed client connection
        if self.request.connection.stream.closed():
            return None
        self.finish({"posts": posts,"idThread": idThread,"isOpPost": isOpPost})


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/api/1\.0/stream/(\w+)", MessageUpdatesHandler),
            (r"/api/1\.0/streamp/(\w+)", MessageNewHandler)
          
        ]
        tornado.web.Application.__init__(self, handlers)


def main():
    tornado.options.parse_command_line()
    app = Application()
    port = int(os.environ.get("PORT", 5000))
    app.listen(port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
