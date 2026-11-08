import socket
import json
import threading
import time
from typing import Dict, Any

class SocketGuardNetworkBridge:
    """[SYS-LOCK-03] Handles low-level OS network socket isolation and dynamic peer coordination."""
    def __init__(self, host: str = "0.0.0.0", port: int = 9090):
        self.host = host
        self.port = port
        self.active_connections: Dict[str, socket.socket] = {}
        self.locked_sockets: Dict[str, bool] = {}
        self.is_running = True

    def enforce_socket_lock(self, node_id: str):
        """Executes SYS-LOCK-03 (RED_BOLT) to clamp socket communications."""
        self.locked_sockets[node_id] = True
        if node_id in self.active_connections:
            try:
                conn = self.active_connections[node_id]
                conn.shutdown(socket.SHUT_RDWR)
                conn.close()
                del self.active_connections[node_id]
                print(f"[🚨 SYS-LOCK-03 ENGAGED] Socket for node '{node_id}' isolated at kernel level.")
            except Exception as e:
                print(f"[ERROR] Failed isolating socket for node {node_id}: {str(e)}")

    def handle_client_node(self, conn: socket.socket, addr: tuple):
        node_id = f"{addr[0]}:{addr[1]}"
        self.active_connections[node_id] = conn
        self.locked_sockets[node_id] = False
        print(f"[🔵 NODE CONNECTED] Peer node registered: {node_id}")

        try:
            while self.is_running:
                if self.locked_sockets.get(node_id, False):
                    break
                data = conn.recv(4096)
                if not data:
                    break
                
                payload = json.loads(data.decode('utf-8'))
                state_coordinates = payload.get("state", [1.0, 1.0, 1.0, 1.0])
                
                # Direct El-Spei Hadamard Check at network layer
                if any(c <= 0 for c in state_coordinates):
                    self.enforce_socket_lock(node_id)
                    break
                
                response = {"status": "GREEN_STATUS", "node_id": node_id, "timestamp": time.time()}
                conn.sendall(json.dumps(response).encode('utf-8'))
        except (ConnectionResetError, json.JSONDecodeError):
            pass
        finally:
            if node_id in self.active_connections:
                conn.close()
                del self.active_connections[node_id]
            print(f"[⚪ NODE DISCONNECTED] Socket closed for: {node_id}")

    def start_network_bridge(self):
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((self.host, self.port))
        server_sock.listen(100)
        print(f"[🟢 NETWORK BRIDGE ACTIVE] Listening for peer node streams on {self.host}:{self.port}...")

        while self.is_running:
            try:
                conn, addr = server_sock.accept()
                client_thread = threading.Thread(target=self.handle_client_node, args=(conn, addr))
                client_thread.daemon = True
                client_thread.start()
            except KeyboardInterrupt:
                self.is_running = False
                break
        server_sock.close()

if __name__ == "__main__":
    bridge = SocketGuardNetworkBridge()
    bridge.start_network_bridge()
