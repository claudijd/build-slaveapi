import logging
from urlparse import parse_qs

from gevent import queue, spawn
from gevent.event import Event

from .actions import reboot

log = logging.getLogger(__name__)

class Processor(object):
    max_jobs = 20

    def __init__(self, messages, concurrency):
        self.messages = messages
        self.concurrency = concurrency

        self.stopped = False
        self.workers = []
        self.work_queue = queue.Queue()

    def add_work(self, slave, action, *args, **kwargs):
        e = Event()
        item = (slave, action, args, kwargs, e)
        log.debug("Adding work to queue: %s", item)
        self.work_queue.put(item)
        self._start_worker()
        return e

    def _start_worker(self):
        if len(self.workers) < self.concurrency:
            log.debug("Spawning new worker")
            t = spawn(self._worker)
            t.link(self._worker_done)
            self.workers.append(t)

    def _worker_done(self, t):
        self.workers.remove(t)
        if self.work_queue.qsize() and not self.stopped:
            self._start_worker()

    def _worker(self):
        jobs = 0
        while True:
            e = None
            try:
                jobs += 1
                try:
                    item = self.work_queue.get(block=False)
                    if not item:
                        break
                except queue.Empty:
                    break

                log.debug("Processing item: %s", item)
                slave, action, args, kwargs, e = item
                action(slave, *args, **kwargs)

                self.messages.put("done", item)

                # todo, bail after max jobs
                if jobs >= self.max_jobs:
                    break
            except:
                log.exception("Something went wrong while processing!")
                if item:
                    log.exception("Item was: %s", item)
                self.messages.put("error", item)
            finally:
                if e:
                    e.set()


class SlaveAPIWSGIApp(object):
    def __init__(self, concurrency=4):
        self.pending = {}
        self.messages = queue.Queue()

        self.processor = Processor(self.messages, concurrency)
        self._message_loop = spawn(self.process_messages)

    def stop(self):
        self._message_loop.kill()

    def __call__(self, environ, start_response):
        # /<slave>/...
        method = getattr(self, "do_%s" % environ["REQUEST_METHOD"], None)
        if not method:
            start_response("405 Method Not Allowed", [])
            return ""
        return method(environ, start_response)

    def do_GET(self, environ, start_response):
        try:
            log.debug("Processing GET request to %s", environ["PATH_INFO"])
            _, _, slave, parts = environ["PATH_INFO"].split("/", 3)
            parts = parts.split("/")
            qs = parse_qs(environ["QUERY_STRING"]
            if parts[0] == "action":
                if parts[1] == "reboot":
                    requestid = environ["QUERY_STRING"][

    def do_POST(self, environ, start_response):
        try:
            log.debug("Processing POST request to %s", environ["PATH_INFO"])
            _, _, slave, parts = environ["PATH_INFO"].split("/", 3)
            parts = parts.split("/")
            headers = []
            if parts[0] == "action":
                if parts[1] == "reboot":
                    if (slave, "reboot") not in self.pending:
                        e = self.processor.add_work(slave, reboot)
                        self.pending[(slave, "reboot")] = e
                    else:
                        e = self.pending[(slave, "reboot")]
                    headers.append(("X-Pending", "True"))

            start_response("202 In queue", [])
            yield json.dumps([{"requestid": id(e)})
            return

        except:
            log.exception("Can't figure out how to handle POST request to %s", environ["PATH_INFO"])
            start_response("400 Bad Request", [])
            return

    def process_messages(self):
        while True:
            msg = self.messages.get()
            log.debug("Got message: %s", msg)
            try:
                # dispatch different message types based on msg[0]
                pass
            except:
                log.exception("Failed to handle message: %s", msg)
