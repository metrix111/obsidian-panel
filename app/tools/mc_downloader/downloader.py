__author__ = "Nigshoxiz"
from urllib.error import HTTPError
from urllib.request import urlopen, Request
import os, ssl, json, inspect, random, string, copy, time, traceback, threading, shutil
from app.utils import is_debug
# add logger
from ob_logger import Logger
logger = Logger("dlMC", debug=is_debug())

class AbruptException(Exception):
    def __init__(self):
        Exception.__init__(self)

    def __str__(self):
        return "Just an exception!"

class DownloaderPool(object):

    instance = None
    def __init__(self):
        self.pool = {}

        pass

    @staticmethod
    def getInstance():
        if DownloaderPool.instance == None:
            DownloaderPool.instance = DownloaderPool()
        return DownloaderPool.instance

    def newTask(self, url, **kwargs):
        """
        :param downloader_instance:
        :return: (instance, instance hash)
        """
        def _finish(e, file):
            self.remove(_hash)

        dt_inst = DownloaderThread(url, **kwargs)
        dt_inst.dl.addDownloadFinishHook(_finish)

        _hash = dt_inst.hash()
        self.pool[_hash] = dt_inst
        return (dt_inst.dl, _hash)

    def get(self, downloader_hash):
        return self.pool.get(downloader_hash)

    def remove(self, downloader_hash):
        _inst = self.pool.get(downloader_hash)
        if _inst != None:
            #_inst.dl.__del__()
            del self.pool[downloader_hash]

    def start(self, downloader_hash):
        _inst = self.pool.get(downloader_hash)
        _inst.setDaemon(True)
        # just start a thread
        _inst.start()

    def pause(self, downloader_hash):
        _inst = self.pool.get(downloader_hash)
        if _inst != None:
            _inst.dl.stop()

    def terminate(self, downloader_hash):
        _inst = self.pool.get(downloader_hash)
        _download_dir = _inst.dl.download_dir
        _filename = _inst.dl.filename
        if _inst != None:
            try:
                _inst.dl.stop()
                # time.sleep(0.5)
                del self.pool[downloader_hash]
            finally:
                # finally , remove files
                _tmp_file = os.path.join(_download_dir, _filename + ".tmp")
                _report_file = os.path.join(_download_dir, _filename + ".report")
                if os.path.exists(_tmp_file):
                    os.remove(_tmp_file)

                if os.path.exists(_report_file):
                    os.remove(_report_file)
                _inst.dl.stopping = False

    def resume(self, downloader_hash):

        _inst = self.pool.get(downloader_hash)
        _inst.dl.stopping = False
        #print(_inst)
        #if _inst != None:
            # copy Downloader object
        #    _dl_obj = copy.copy(_inst.dl)
        #    # remove old thread
        #    self.remove(downloader_hash)
        #    new_dt_inst = DownloaderThread('',_dl = _dl_obj)
        #    self.pool[downloader_hash] = new_dt_inst
        #    new_dt_inst.start()
        #pass

class DownloaderThread(threading.Thread):

    def __init__(self, url, _dl = None, **kwargs):
        super(DownloaderThread, self).__init__()

        if isinstance(_dl, Downloader):
            self.dl = _dl
            self.dl._reopen_file()
        else:
            self.dl = Downloader(url, **kwargs)

    def run(self):
        self.dl.download()

    def hash(self):
        return self.dl.__hash__()

class Downloader(object):

    def __init__(self, url,
                 force_multithread=False,
                 force_singlethread=False,
                 fail_clear=True,  # when download fails, clear tmp (report)file
                 download_dir=""):
        self.url = url
        self.filesize = 0
        self.support_range = False
        self.timeout = 10
        self.threads = []

        self.lock = threading.Lock()

        self.force_multithread  = force_multithread
        self.force_singlethread = force_singlethread
        self.fail_clear = fail_clear
        self.download_dir = download_dir

        self.dw_type_flag = None
        self.download_correct_flag = True
        self.slices = []

        self.THREADS_NUM = 4

        self._download_finish_hook = []
        self._network_error_hook = []

        # SSL context
        self.ssl_ctx = None
        self.headers = {}

        self.stopping = False
        # response
        try:
            # get filename from url
            self.filename = self.url.split("/")[-1]
            _tmp_file = os.path.join(self.download_dir, self.filename + ".tmp")
            _, __ = self._read_report()
            if __ == None:
                self.fd = open(_tmp_file, "wb")
            else:
                self.fd = open(_tmp_file, "r+b")
        except:
            self.fd.close()

    # del constructor. After all, all d
    def __del__(self):
        self.fd.close()

    def __hash__(self):
        return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(16))

    def set_force_multithread(self, val):
        self.force_multithread = val

    def set_force_singlethread(self, val):
        self.force_singlethread = val

    def set_fail_clear(self, val):
        self.fail_clear = val

    def setThreads(self,thread_num):
        """
        indicate the number of creating threads when using
        multithread download mode.
        :param thread_num: the number of threads to create. Default is 8.
        :return:
        """
        self.THREADS_NUM = thread_num

    def setHeaders(self,headers):
        self.headers = headers

    def analyse(self,headers):
        req = Request(url=self.url, method="HEAD")
        req.add_header("Range","bytes=0-")

        for i in headers:
            req.add_header(i, headers.get(i))
        try:
            logger.info("start analysing URL...")
            result = urlopen(req, timeout=15)

            headers = result.info()
            _len = headers.get("Content-Length")
            if _len == None:
                self.filesize = -1
            else:
                self.filesize = int(_len)

            if result.getcode() == 206:
                self.support_range = True
            else:
                self.support_range = False

        except:
            self.support_range = False
            self.filesize = -1

    def disableSSLCert(self):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        self.ssl_ctx = ctx

    # just a wrapper :-)
    def addDownloadFinishHook(self,fn):
        if inspect.isfunction(fn) or inspect.ismethod(fn):
            self._download_finish_hook.append(fn)

    def addNetworkErrorHook(self, fn):
        if inspect.isfunction(fn) or inspect.ismethod(fn):
            self._network_error_hook.append(fn)

    # terminate downloading and remove tmp file
    # WARNING : this operation will remove tep file PERMANENTLY!
    def clear(self):
        _tmp_file = os.path.join(self.download_dir, self.filename + ".tmp")
        _report_file = os.path.join(self.download_dir, self.filename + ".report")
        if os.path.exists(_tmp_file):
            os.remove(_tmp_file)

        if os.path.exists(_report_file):
            os.remove(_report_file)

    def getProgress(self):
        """
        get downloaded size of file
        :return:
        """
        if self.dw_type_flag == "single":
            _tmp_file = os.path.join(self.download_dir, self.filename + ".tmp")
            if os.path.exists(_tmp_file):
                _size = os.path.getsize(_tmp_file)
                return (_size, self.filesize)
            else:
                return (0, self.filesize)
        elif self.dw_type_flag == "multi":
            _total = 0
            for si in self.slices:
                _total += si[1]

            _, __  = self._read_report()

            if __ != None:
                for _si in __:
                    _total += _si[1]

            return (_total, self.filesize)
        else:
            return (None, self.filesize)

    def _make_report(self):
        _report_file = os.path.join(self.download_dir, self.filename + ".report")
        # generate *.report file when download process is abnormally terminated.
        # it is a json file , like:
        # {
        #   "support_range" : True | False,
        #   "slices": [(<index,file_size>)]
        # }
        # slices = None when ranging download is not supported.
        rtn = {
            "support_range": self.support_range,
            "slices": self.slices
        }
        f = open(_report_file, "w+")
        f.write(json.dumps(rtn))
        f.close()

    def _read_report(self):
        _filename = os.path.join(self.download_dir, self.filename+".report")

        if os.path.isfile(_filename):
            f = open(_filename,"r")
            try:
                r = json.loads(f.read())
                return r.get("support_range") , r.get("slices")
            except:
                return None, None
        else:
            return None, None

    # when fd has been abruptly closed, this function is to recover it
    def _reopen_file(self):
        try:
            # get filename from url
            self.filename = self.url.split("/")[-1]
            _tmp_file = os.path.join(self.download_dir, self.filename + ".tmp")
            _ , __ = self._read_report()

            if self.fd.closed == False:
                self.fd.close()
            if __ == None:
                self.fd = open(_tmp_file, "wb")
            else:
                self.fd = open(_tmp_file, "r+b")
        except:
            self.fd.close()

    def stop(self):
        self.stopping = True

    def download(self):
        def _download_singlethread():
            while True:
                logger.info("Mode: directly downloading")
                self._reopen_file()
                self.fd.seek(0,0)
                self.dw_type_flag = "single"
                try:
                    req = Request(url=self.url, headers=self.headers)
                    resp = urlopen(req, context=self.ssl_ctx, timeout=self.timeout)

                    if self.filesize < 0:
                        _header = resp.info()
                        _len = _header.get("Content-Length")
                        self.filesize = _len

                    #self.fd.write(resp.read())
                    #shutil.copyfileobj(resp, self.fd,length=8*1024)
                    while not self.stopping:
                       buf = resp.read(32 * 1024)
                       if not buf:
                           break
                       self.fd.write(buf)

                    time.sleep(1)
                    if self.stopping == True:
                        while self.stopping:
                            time.sleep(1)
                        continue

                except HTTPError:
                    logger.error(traceback.format_exc())
                    return False
                except:
                    logger.error(traceback.format_exc())
                    return False
                return True

        def _download_multithread():
            self.dw_type_flag = "multi"
            while True:
                _, slices = self._read_report()

                _tmp_file = os.path.join(self.download_dir, self.filename + ".tmp")
                __exists  = os.path.exists(_tmp_file)

                ranges = []
                if slices != None and __exists == True:
                    for item in slices:
                        item[0] = int(item[0])
                        item[1] = int(item[1])
                        item[2] = int(item[2])

                        if item[0] + item[1] - 1 < item[2]:
                            ranges.append( (item[0] + item[1], item[2]) )
                    self._reopen_file()
                    logger.info("Resume Downloading")
                else:
                    ranges = self._split_range()

                logger.info("Start Downloading... threads = %s" % len(ranges))
                _i = 0
                for threads in range(len(ranges)):
                    self.slices.append([ranges[_i][0], 0, ranges[_i][1]])

                    range_item = ranges[_i]
                    t = threading.Thread(target=self.download_thread, args=(range_item, _i))
                    t.setDaemon(True)
                    t.start()
                    self.threads.append(t)
                    _i += 1

                try:
                    for t in self.threads:
                        t.join()
                except AbruptException:
                    self._make_report()
                    return False

                # pause
                if self.stopping == True:
                    # clear old data
                    self._make_report()
                    self.slices = []
                    self.threads = []
                    while self.stopping:
                        time.sleep(1)
                    continue

                if self.download_correct_flag == True:
                    return True
                else:
                    self._make_report()
                    return False

        # get filesize, Partial Support, etc.
        self.analyse(self.headers)

        if self.force_multithread:
            result = _download_multithread()
        elif self.force_singlethread:
            result = _download_singlethread()
        else:
            if self.support_range == True:
                result = _download_multithread()
            else:
                result = _download_singlethread()

        logger.info("Download finish! result = %s" % result)
        # after file is successfully downloaded
        if result:
            __repeat_file_counter = 0
            _fn = os.path.join(self.download_dir, self.filename)
            _filename = _fn

            shutil.move(_filename + ".tmp", _filename)
            #while True:
            #    if os.path.exists(_filename):
            #        __repeat_file_counter += 1
            #        _filename = _fn + "." + str(__repeat_file_counter)
            #    else:
            #        _tmp_file = _fn + ".tmp"
            #        shutil.move(_tmp_file, _filename)
            #        break

            _report_file = os.path.join(self.download_dir, self.filename + ".report")
            if os.path.exists(_report_file):
                os.remove(_report_file)

            # run finish hook
            for _hook in self._download_finish_hook:
                if inspect.isfunction(_hook) or inspect.ismethod(_hook):
                    _hook(True, _filename)
        else:
            # fisrt clear file
            if self.fail_clear:
                self.clear()
            # next run network error hook
            # run finish hook
            for _hook in self._network_error_hook:
                if inspect.isfunction(_hook) or inspect.ismethod(_hook):
                    _hook(None)

        return result

    def _split_range(self):
        if self.filesize < 0:
            return []
        onceDownloadSize = int(self.filesize / self.THREADS_NUM)
        ranges = []
        _index = 0

        while True:
            if _index + onceDownloadSize * 2 > self.filesize:
                ranges.append((_index, self.filesize - 1))
                break
            else:
                ranges.append((_index, _index + onceDownloadSize - 1))
                _index += onceDownloadSize

        return ranges

    def download_thread(self, range_item, _index):
        _out_break = False
        MAX_RETRY = 5

        req = Request(url=self.url)
        req.add_header("Range", "bytes=%s-%s" % range_item)
        # add header
        for i in self.headers:
            req.add_header(i, self.headers.get(i))

        retry = 0
        while True:
            if _out_break == True:
                break
            try:
                resp = urlopen(req, timeout=self.timeout, context=self.ssl_ctx)
            except TypeError:
                logger.error(traceback.format_exc())
                logger.debug("TypeError")
                if self.lock.locked():
                    self.lock.release()

                self.download_correct_flag = False
                break
            except:
                logger.error(traceback.format_exc())
                logger.debug("%s - HTTP connection error %s - %s" % (
                    threading.current_thread().getName(), range_item[0], range_item[1]))
                retry += 1
                if retry <= MAX_RETRY:
                    logger.debug("retry %s time" % retry)

                if self.lock.locked():
                    self.lock.release()

                if retry == MAX_RETRY + 1:
                    self.download_correct_flag = False
                    break
                else:
                    continue

            # slices format: [<start size>, <downloaded size>,<end size>]
            _download_slice = self.slices[_index][1]

            _range_item = [0, 0]
            _range_item[0] = range_item[0] + _download_slice
            _range_item[1] = range_item[1]

            try:
                # read data
                while True:
                    if self.stopping:
                        _out_break = True
                        break

                    # when network error triggered
                    if not self.download_correct_flag:
                        _out_break = True
                        break

                    buf = resp.read(4 * 1024)
                    if not buf:
                        break
                    self.lock.acquire()
                    self.fd.seek(_range_item[0] + self.slices[_index][1], 0)
                    self.fd.write(buf)
                    self.slices[_index][1] += len(buf)
                    self.lock.release()

                # shutil.copyfileobj(resp, self.fd)
                logger.debug("%s finished!" % threading.current_thread().getName())
                break
            except:
                logger.error(traceback.format_exc())
                retry += 1
                if retry <= MAX_RETRY:
                    logger.debug("retry %s time" % retry)

                if self.lock.locked():
                    self.lock.release()

                if retry == MAX_RETRY + 1:
                    self.download_correct_flag = False
                    break
                else:
                    continue
