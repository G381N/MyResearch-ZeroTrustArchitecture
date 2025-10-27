import asyncio
import psutil
import time
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Callable, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging
import os
import subprocess
import json

logger = logging.getLogger(__name__)

class EventCollector:
    def __init__(self):
        self.is_collecting = False
        self.event_callback: Optional[Callable] = None
        self.file_observer = None
        self.process_cache = {}
        self.network_cache = {}
        self.last_auth_log_position = 0
        # Will be set to the asyncio event loop when collection starts
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        
    def set_event_callback(self, callback: Callable):
        """Set callback function to handle collected events"""
        self.event_callback = callback
    
    async def start_collection(self):
        """Start collecting system events"""
        if self.is_collecting:
            logger.warning("Event collection already started")
            return
        
        self.is_collecting = True
        logger.info("Starting event collection")
        
        # Start background tasks
        # capture the running loop so file-watch callbacks (which run on a
        # watchdog thread) can schedule coroutines safely using
        # asyncio.run_coroutine_threadsafe
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            # fallback: get_event_loop may return a loop
            self._loop = asyncio.get_event_loop()

        asyncio.create_task(self._monitor_processes())
        asyncio.create_task(self._monitor_network())
        asyncio.create_task(self._monitor_auth_log())
        self._start_file_monitoring()
        
        logger.info("Event collection started successfully")
    
    async def stop_collection(self):
        """Stop collecting system events"""
        self.is_collecting = False
        
        if self.file_observer:
            self.file_observer.stop()
            self.file_observer.join()
        
        logger.info("Event collection stopped")
    
    async def _monitor_processes(self):
        """Monitor process start/end events"""
        previous_processes = set()
        
        while self.is_collecting:
            try:
                current_processes = set()
                
                for proc in psutil.process_iter(['pid', 'name', 'create_time', 'username']):
                    try:
                        proc_info = proc.info
                        current_processes.add(proc_info['pid'])
                        
                        # Check for new processes
                        if proc_info['pid'] not in previous_processes:
                            await self._emit_event('process_start', {
                                'pid': proc_info['pid'],
                                'process_name': proc_info['name'],
                                'username': proc_info['username'],
                                'create_time': proc_info['create_time']
                            })
                        
                        # Cache process info
                        self.process_cache[proc_info['pid']] = {
                            'name': proc_info['name'],
                            'username': proc_info['username'],
                            'create_time': proc_info['create_time']
                        }
                        
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                
                # Check for ended processes
                ended_processes = previous_processes - current_processes
                for pid in ended_processes:
                    if pid in self.process_cache:
                        proc_info = self.process_cache[pid]
                        await self._emit_event('process_end', {
                            'pid': pid,
                            'process_name': proc_info['name'],
                            'username': proc_info['username'],
                            'create_time': proc_info['create_time']
                        })
                        del self.process_cache[pid]
                
                previous_processes = current_processes
                
            except Exception as e:
                logger.error(f"Error monitoring processes: {e}")
            
            await asyncio.sleep(1)  # Check every second
    
    async def _monitor_network(self):
        """Monitor network connection events"""
        previous_connections = set()
        
        while self.is_collecting:
            try:
                current_connections = set()
                
                for conn in psutil.net_connections(kind='inet'):
                    if conn.status == 'ESTABLISHED':
                        conn_id = f"{conn.laddr.ip}:{conn.laddr.port}-{conn.raddr.ip}:{conn.raddr.port}"
                        current_connections.add(conn_id)
                        
                        # Check for new connections
                        if conn_id not in previous_connections:
                            await self._emit_event('network_connection', {
                                'local_address': f"{conn.laddr.ip}:{conn.laddr.port}",
                                'remote_address': f"{conn.raddr.ip}:{conn.raddr.port}",
                                'status': conn.status,
                                'pid': conn.pid,
                                'process_name': self._get_process_name(conn.pid)
                            })
                
                previous_connections = current_connections
                
            except Exception as e:
                logger.error(f"Error monitoring network: {e}")
            
            await asyncio.sleep(2)  # Check every 2 seconds
    
    async def _monitor_auth_log(self):
        """Monitor authentication events from system logs"""
        auth_log_path = '/var/log/auth.log'
        
        if not os.path.exists(auth_log_path):
            logger.warning(f"Auth log not found at {auth_log_path}")
            return
        
        while self.is_collecting:
            try:
                with open(auth_log_path, 'r') as f:
                    f.seek(self.last_auth_log_position)
                    new_lines = f.readlines()
                    self.last_auth_log_position = f.tell()
                
                for line in new_lines:
                    await self._parse_auth_log_line(line)
                    
            except Exception as e:
                logger.error(f"Error monitoring auth log: {e}")
            
            await asyncio.sleep(1)
    
    async def _parse_auth_log_line(self, line: str):
        """Parse authentication log line for events"""
        line_lower = line.lower()
        
        # Login events
        if 'session opened' in line_lower or 'accepted' in line_lower:
            await self._emit_event('login', {
                'log_line': line.strip(),
                'timestamp': self._extract_timestamp(line),
                'auth_success': True
            })
        
        # Logout events
        elif 'session closed' in line_lower or 'disconnected' in line_lower:
            await self._emit_event('logout', {
                'log_line': line.strip(),
                'timestamp': self._extract_timestamp(line),
                'auth_success': True
            })
        
        # Auth failure events
        elif 'failed' in line_lower or 'authentication failure' in line_lower:
            await self._emit_event('auth_failure', {
                'log_line': line.strip(),
                'timestamp': self._extract_timestamp(line),
                'auth_success': False
            })
        
        # Sudo command events
        elif 'sudo:' in line_lower and 'command' in line_lower:
            await self._emit_event('sudo_command', {
                'log_line': line.strip(),
                'timestamp': self._extract_timestamp(line),
                'command': self._extract_sudo_command(line)
            })
    
    def _start_file_monitoring(self):
        """Start monitoring file system changes"""
        try:
            # Monitor common system directories
            watch_dirs = ['/etc', '/home', '/var/log']
            
            for watch_dir in watch_dirs:
                if os.path.exists(watch_dir):
                    self.file_observer = Observer()
                    # pass the loop into the handler so it can schedule
                    # coroutine callbacks from the watchdog thread safely
                    handler = FileChangeHandler(self._on_file_change, loop=self._loop)
                    self.file_observer.schedule(handler, watch_dir, recursive=True)
                    self.file_observer.start()
                    logger.info(f"Started monitoring {watch_dir}")
                    break
        except Exception as e:
            logger.error(f"Error starting file monitoring: {e}")
    
    async def _on_file_change(self, event_type: str, file_path: str):
        """Handle file system change events"""
        # Filter out temporary files and logs
        if any(skip in file_path for skip in ['.tmp', '.log', '.cache', '.swp']):
            return
        
        await self._emit_event('file_change', {
            'event_type': event_type,
            'file_path': file_path,
            'file_size': self._get_file_size(file_path),
            'severity': self._assess_file_change_severity(file_path)
        })
    
    def _get_process_name(self, pid: int) -> str:
        """Get process name by PID"""
        try:
            return psutil.Process(pid).name()
        except:
            return "unknown"
    
    def _extract_timestamp(self, log_line: str) -> str:
        """Extract timestamp from log line"""
        try:
            # Extract first part of log line (timestamp)
            parts = log_line.split()
            if len(parts) >= 3:
                return f"{parts[0]} {parts[1]} {parts[2]}"
        except:
            pass
        return datetime.now().isoformat()
    
    def _extract_sudo_command(self, log_line: str) -> str:
        """Extract sudo command from log line"""
        try:
            if 'COMMAND=' in log_line:
                return log_line.split('COMMAND=')[1].strip()
        except:
            pass
        return "unknown"
    
    def _get_file_size(self, file_path: str) -> int:
        """Get file size"""
        try:
            return os.path.getsize(file_path)
        except:
            return 0
    
    def _assess_file_change_severity(self, file_path: str) -> int:
        """Assess severity of file change (1-10 scale)"""
        high_risk_paths = ['/etc/passwd', '/etc/shadow', '/etc/sudoers', '/etc/ssh']
        medium_risk_paths = ['/etc', '/home']
        
        if any(risk_path in file_path for risk_path in high_risk_paths):
            return 8
        elif any(risk_path in file_path for risk_path in medium_risk_paths):
            return 5
        else:
            return 2
    
    async def _emit_event(self, event_type: str, metadata: Dict[str, Any]):
        """Emit event to callback"""
        if not self.event_callback:
            return
        
        event = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'metadata': metadata
        }
        
        try:
            await self.event_callback(event)
        except Exception as e:
            logger.error(f"Error emitting event: {e}")

class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, callback, loop: Optional[asyncio.AbstractEventLoop] = None):
        self.callback = callback
        # The loop will normally be the main application's running loop. If
        # it's None, we'll try to obtain it when scheduling.
        self._loop = loop

    def _schedule(self, event_type: str, path: str):
        # Schedule the coroutine on the main loop from the watchdog thread.
        loop = self._loop
        if loop is None:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                try:
                    loop = asyncio.get_event_loop()
                except Exception:
                    loop = None

        if loop is not None:
            try:
                asyncio.run_coroutine_threadsafe(self.callback(event_type, path), loop)
            except Exception:
                # Last resort: try scheduling with create_task if we're on loop
                try:
                    loop.call_soon_threadsafe(lambda: asyncio.create_task(self.callback(event_type, path)))
                except Exception as e:
                    logger.error(f"Failed to schedule file change callback: {e}")
        else:
            logger.error("No event loop available to schedule file change callback")

    def on_modified(self, event):
        if not event.is_directory:
            self._schedule('modified', event.src_path)

    def on_created(self, event):
        if not event.is_directory:
            self._schedule('created', event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            self._schedule('deleted', event.src_path)

# Global event collector instance
event_collector = EventCollector()
