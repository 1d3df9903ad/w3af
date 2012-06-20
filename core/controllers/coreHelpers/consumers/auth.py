'''
auth.py

Copyright 2012 Andres Riancho

This file is part of w3af, w3af.sourceforge.net .

w3af is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation version 2 of the License.

w3af is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with w3af; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

'''
import threading
import time
import sys
import Queue

from .constants import FINISH_CONSUMER, FORCE_LOGIN

from core.controllers.coreHelpers.exception_handler import exception_handler
from core.controllers.exception_handling.helpers import pprint_plugins



class auth(threading.Thread):
    '''
    Thread that logins into the application every N seconds.
    '''
    
    def __init__(self, in_queue, auth_plugins, w3af_core, timeout):
        '''
        @param in_queue: A queue that's used to communicate with the thread. Items
                         that might appear in this queue are:
                             * FINISH_CONSUMER
                             * FORCE_LOGIN
        @param auth_plugins: Instances of auth plugins in a list
        @param w3af_core: The w3af core that we'll use for status reporting
        @param timeout: The time to wait between each login check
        '''
        super(auth, self).__init__()
        
        self._in_queue = in_queue
        self._auth_plugins = auth_plugins
        self._w3af_core = w3af_core
        self._timeout = timeout
    
    def run(self):
        '''
        Consume the queue items
        '''
        while True:
           
            try:
                action = self._in_queue.get( timeout=self._timeout )
            except Queue.Empty:
                self._login()
            else:
                
                if action == FINISH_CONSUMER:
                    
                    for plugin in self._auth_plugins:
                        plugin.end()
                    break
                    
                elif action == FORCE_LOGIN:
                    
                    self._login()

    def _login(self):
        '''
        This is the method that actually calls the plugins in order to login
        to the web application.        
        '''
        for plugin in self._auth_plugins:
            try:
                if not plugin.is_logged():
                    plugin.login()
            except Exception, e:
                # Smart error handling, much better than just crashing.
                # Doing this here and not with something similar to:
                # sys.excepthook = handle_crash because we want to handle
                # plugin exceptions in this way, and not framework 
                # exceptions                        
                exec_info = sys.exc_info()
                enabled_plugins = pprint_plugins(self._w3af_core)
                exception_handler.handle( self._w3af_core.status, e , 
                                          exec_info, enabled_plugins )
    
    def async_force_login(self):
        self._in_queue.put( FORCE_LOGIN )
    
    def force_login(self):
        self._login()
        
    def stop(self):
        '''
        Poison the loop
        '''
        self._in_queue.put( FINISH_CONSUMER )
        #
        #    Allow some time for the plugins to properly end before anything
        #    else is done at the core level.
        #
        time.sleep(0.5)
        
