__author__ = "Nigshoxiz"

from . import logger, SERVER_STATE, Singleton
from .process_pool import MCProcessPool
from .process import MCProcess
from .daemon_manager import MCDaemonManager
from .instance_info import MCInstanceInfo
from .mc_config import MCWrapperConfig
from .process_callback import MCProcessCallback
from .info_monitor import MCInstanceInfoMonitor

from app.controller.global_config import GlobalConfig

import pyuv, os, threading, math, signal

class Watcher(metaclass=Singleton):
    def __init__(self):
        self._loop = pyuv.Loop()
        """
        Is Event Loop running?
        If not, and _active_count > 0 (i.e. some processes need loop to handle!)
        Just create a thread execute `loop.run()`
        """

        self.proc_pool = MCProcessPool()
        self.callback  = MCProcessCallback()
        self.info_monitor = MCInstanceInfoMonitor(self._loop)

        self._init_proc_pool()

        self._signal_handle = pyuv.Signal(self._loop)
        pass

    def _signal_callback(self, handle, signum):
        # TODO close server properly
        logger.debug("recv quit signal %s" % signum)
        pass

    def _add_instance_to_pool(self, db_item):
        # db_item = db.session.query(ServerInstance).join(JavaBinary).join(ServerCORE).filter(**).first()
        # init config
        item = db_item
        mc_w_config = {
            "jar_file": os.path.join(item.ob_server_core.file_dir, item.ob_server_core.file_name),
            "java_bin": item.ob_java_bin.bin_directory,
            "max_RAM": int(item.max_RAM),
            "max_player" : int(item.max_user),
            "min_RAM": math.floor(int(item.max_RAM) / 2),
            "proc_cwd": item.inst_dir,
            "port": item.listening_port
        }

        info = {
            "owner": item.owner_id,
            "inst_id" : item.inst_id
        }

        # adding initial data into proc_pool
        _model = {
            "config" : MCWrapperConfig(**mc_w_config),
            "status" : SERVER_STATE.HALT,
            "daemon" : MCDaemonManager(),
            "info"   : MCInstanceInfo(**info),
            "proc"   : MCProcess(item.inst_id, self._loop)
        }

        self.proc_pool.add(item.inst_id, _model)

    def _init_proc_pool(self):
        gc = GlobalConfig()

        # first, we have to make sure that database has been
        # initialized.
        if gc.get("init_super_admin") == True:
            # import dependencies here to prevent circular import
            from app import db
            from app.model import ServerInstance, JavaBinary, ServerCORE

            # search
            _q = db.session.query(ServerInstance).join(JavaBinary).join(ServerCORE).all()
            if _q == None:
                return None
            for item in _q:
                self._add_instance_to_pool(item)
            return True
        else:
            return None

    def launch_loop(self):
        # add handle
        self._signal_handle.start(self._signal_callback, signal.SIGINT)
        self._loop.run()
        logger.info("Loop Finish!")

    def start_instance(self, inst_id):
        inst_obj = self.proc_pool.get(inst_id)

        if inst_obj == None:
            return None
        _proc    = inst_obj.get("proc")
        _status  = inst_obj.get("status")
        _daemon  = inst_obj.get("daemon")
        mc_w_config  = inst_obj.get("config")

        # reload config
        _proc.load_config(mc_w_config)

        # make sure status is HALT, or just skip it because
        # there's already an running instance.
        if _status != SERVER_STATE.HALT:
            return None

        # start process
        _proc.start_process()
        # reset crash count
        _daemon.reset_crash_count()

        # start timer
        self.info_monitor.start_timer()

    def stop_instance(self, inst_id):
        inst_obj = self.proc_pool.get(inst_id)

        if inst_obj == None:
            return None
        _proc    = inst_obj.get("proc")
        _status  = inst_obj.get("status")

        # the stop callback shall do the work of marking the new status (HALT)
        # and deduct active count. Don't do them HERE!
        _proc.stop_process()

    def terminate_instance(self, inst_id):
        inst_obj = self.proc_pool.get(inst_id)

        if inst_obj == None:
            return None
        _proc    = inst_obj.get("proc")
        _status  = inst_obj.get("status")

        _proc.terminate_process()

    def send_command(self, inst_id, command):
        inst_obj = self.proc_pool.get(inst_id)

        if inst_obj == None:
            return None
        _proc    = inst_obj.get("proc")
        _status  = inst_obj.get("status")
        _daemon  = inst_obj.get("daemon")
        _info    = inst_obj.get("info")

        # limit max command length to send
        if _status == SERVER_STATE.RUNNING and len(command) < 1000:

            # if input 'stop', just stop it, do not restart the server.
            # Because this command is surely propmted by user.
            if command == "stop":
                _daemon.set_normal_exit(True)

            _proc.send_command(command)
            # record the input into log object
            _cmd_log = "⟹ %s\n" % command
            _info.append_log(0,_cmd_log)
