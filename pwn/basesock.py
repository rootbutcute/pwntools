import pwn, socket, time, sys, re, errno
from log import *
from consts import *
from util import size
from threading import Thread

class basesock:
    def settimeout(self, n):
        self.timeout = n
        self.sock.settimeout(n)

    def setblocking(self, b):
        self.sock.setblocking(b)

    def connected(self):
        return self.sock <> None

    def close(self):
        if self.sock:
            self.sock.close()
            self.sock = None
            info('Closed connection to %s on port %d' % self.target)

    def _send(self, dat):
        l = len(dat)
        i = 0
        while l > i:
            i += self.sock.send(dat[i:])

    def send(self, dat):
        if self.checked:
            try:
                self._send(dat)
            except socket.error, e:
                if e.errno == errno.EPIPE:
                    failure('Broken pipe')
                    sys.exit(PWN_UNAVAILABLE)
                else:
                    raise
        else:
            self._send(dat)

    def recv(self, numb = 4096):
        if self.checked:
            try:
                res = self.sock.recv(numb)
            except socket.timeout:
                failure('Connection timed out')
                sys.exit(PWN_UNAVAILABLE)
        else:
            res = self.sock.recv(numb)
        if self.debug:
            sys.stderr.write(res)
            sys.stderr.flush()
        return res

    def recvn(self, numb):
        res = []
        n = 0
        while n < numb:
            c = self.recv(1)
            if not c:
                break
            res.append(c)
            n += 1
        return ''.join(res)

    def recvuntil(self, delim = None, **kwargs):

        if 'regex' in kwargs:
            expr = re.compile(kwargs['regex'], re.DOTALL)
            pred = lambda s: expr.match(s)
        elif 'pred' in kwargs:
            pred = kwargs['pred']
        elif delim != None:
            pred = lambda s: s.endswith(delim)
        else:
            die('recvuntil called without delim, regex or pred')

        res = ''

        while not pred(res):
            c = self.recv(1)
            if not c:
                break

            res += c
        return res

    def sendafter(self, delim, dat):
        res = self.recvuntil(delim)
        self.send(dat)
        return res

    def sendwhen(self, dat, **kwargs):
        res = self.recvuntil(**kwargs)
        self.send(dat)
        return res

    def recvline(self, lines = 1):
        res = []
        for _ in range(lines):
            res.append(self.recvuntil('\n'))
        return ''.join(res)

    def interactive(self, prompt = boldred('$') + ' '):
        info('Switching to interactive mode')
        import rlcompleter
        debug = self.debug
        timeout = self.timeout
        self.debug = False
        self.settimeout(None)
        running = True
        def loop():
            while running:
                sys.stderr.write(self.recv())
                sys.stderr.flush()
        t = Thread(target = loop)
        t.daemon = True
        t.start()
        while True:
            try:
                time.sleep(0.1)
                self.send(raw_input(prompt) + '\n')
            except KeyboardInterrupt:
                self.debug = debug
                self.settimeout(timeout)
                running = False
                sys.stderr.write('Interrupted\n')
                break

    def recvall(self):
        waitfor('Recieving all data')
        r = []
        l = 0
        while True:
            s = self.recv()
            if s == '': break
            r.append(s)
            l += len(s)
            status(size(l))
        self.close()
        return ''.join(r)