import React, { useEffect, useRef } from 'react';
import { Terminal as XTerm } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import 'xterm/css/xterm.css';
import { Box } from '@mui/material';

const Terminal = ({ socketUrl, onData }) => {
  const terminalRef = useRef(null);
  const xtermRef = useRef(null);
  const socketRef = useRef(null);
  const fitAddonRef = useRef(null);

  useEffect(() => {
    // Initialize xterm.js
    const xterm = new XTerm({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: '"Fira Code", monospace',
      theme: {
        background: 'transparent',
        foreground: '#e2e8f0',
        cursor: '#0a84ff',
        selection: 'rgba(10, 132, 255, 0.3)',
        black: '#000000',
        red: '#ff453a',
        green: '#32d74b',
        yellow: '#ffd60a',
        blue: '#0a84ff',
        magenta: '#bf5af2',
        cyan: '#5ac8fa',
        white: '#ffffff',
      }
    });

    const fitAddon = new FitAddon();
    xterm.loadAddon(fitAddon);
    
    xterm.open(terminalRef.current);
    fitAddon.fit();

    xtermRef.current = xterm;
    fitAddonRef.current = fitAddon;

    // Connect WebSocket
    const socket = new WebSocket(socketUrl);
    socketRef.current = socket;

    socket.onopen = () => {
      xterm.writeln('\x1b[1;32mCONNECTED TO GEOSUITE SHELL\x1b[0m');
      
      // Send initial resize
      const dims = {
        type: 'resize',
        cols: xterm.cols,
        rows: xterm.rows
      };
      socket.send(JSON.stringify(dims));
    };

    socket.onmessage = (event) => {
      xterm.write(event.data);
    };

    socket.onclose = () => {
      xterm.writeln('\n\x1b[1;31mDISCONNECTED\x1b[0m');
    };

    // Terminal data -> WebSocket
    xterm.onData((data) => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(data);
      }
    });

    // Handle resize
    const handleResize = () => {
      fitAddon.fit();
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({
          type: 'resize',
          cols: xterm.cols,
          rows: xterm.rows
        }));
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      socket.close();
      xterm.dispose();
    };
  }, [socketUrl]);

  return (
    <Box 
      ref={terminalRef} 
      sx={{ 
        width: '100%', 
        height: '100%', 
        '& .xterm-viewport': { 
          backgroundColor: 'transparent !important',
          '&::-webkit-scrollbar': { width: '8px' },
          '&::-webkit-scrollbar-thumb': { backgroundColor: 'rgba(255,255,255,0.1)', borderRadius: '4px' }
        }
      }} 
    />
  );
};

export default Terminal;
