from __future__ import annotations
import json
import math
import hashlib
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from http.server import BaseHTTPRequestHandler, HTTPServer

# ============================================================
# 1. CORE CYBERNETIC ENGINE CONTROLLER (UGRCK CORE)
# ============================================================

class ExecutionState(Enum):
    AUTHORIZED = "AUTHORIZED"
    MONITORED = "MONITORED"
    ADAPTING = "ADAPTING"
    REGENERATING = "REGENERATING"
    INTERCEPTED = "INTERCEPTED"
    RED_BOLT = "RED_BOLT"
    SYSTEM_LOCK = "SYSTEM_LOCK"

@dataclass
class TargetSystem:
    identifier: str
    domain: str
    state: List[float]
    flows: Dict[str, List[float]]
    lower_bounds: List[float]
    temporal_horizon: int = 50

@dataclass
class ConstraintSet:
    state_floor: float = 1e-9
    flow_rate_floor: float = 0.0
    impact_velocity_floor: float = 0.0
    rho: float = 0.0  # El-Spei Invariant Zero Temporal Discount (rho = 0)
    non_substitution: bool = True

@dataclass
class ImpactResult:
    gradient: List[float]
    dynamic_flow: List[float]
    velocity: List[float]
    impact_velocity: float
    valid: bool
    reason: str

class ElSpeiHadamardGuard:
    """[SYS-HAD-01] Enforces El-Spei's Hadamard Non-Substitution Guard via logarithmic integrity check."""
    @staticmethod
    def validate(state: List[float]) -> bool:
        if any(x <= 0 for x in state):
            return False
        try:
            log_sum = sum(math.log(x) for x in state)
            return math.exp(log_sum) > 0
        except (ValueError, OverflowError):
            return False

class MultiFlowRouterEngine:
    """Active cybernetic coordinator of dynamic inter-domain flows."""
    @staticmethod
    def aggregate(flows: Dict[str, List[float]]) -> List[float]:
        if not flows:
            return []
        dimensions = len(next(iter(flows.values())))
        result = [0.0] * dimensions
        for vector in flows.values():
            for i, value in enumerate(vector):
                result[i] += value
        return result

    @staticmethod
    def hadamard_coordinate(dynamic_matrix: List[float], flow_vector: List[float]) -> List[float]:
        return [m * k for m, k in zip(dynamic_matrix, flow_vector)]

class GenerativeImpactVelocityEngine:
    """[SYS-GIVE-02] GIVE Engine computing impact velocity under zero temporal discount (rho = 0)."""
    def __init__(self, constraints: ConstraintSet):
        self.constraints = constraints

    def compute(self, state: List[float], flow_vector: List[float], gradient: List[float], dynamic_matrix: List[float]) -> ImpactResult:
        if not ElSpeiHadamardGuard.validate(state):
            return ImpactResult(gradient, [], [], 0.0, False, "SYS-HAD-01_HADAMARD_BREACH")
        
        dynamic_flow = MultiFlowRouterEngine.hadamard_coordinate(dynamic_matrix, flow_vector)
        velocity = [g * f * math.exp(-self.constraints.rho) for g, f in zip(gradient, dynamic_flow)]
        impact_velocity = sum(abs(v) for v in velocity)
        valid = (impact_velocity >= self.constraints.impact_velocity_floor)
        return ImpactResult(gradient, dynamic_flow, velocity, impact_velocity, valid, "CLEAR" if valid else "VELOCITY_BREACH")

class PredictiveTrajectoryEngine:
    def __init__(self, constraints: ConstraintSet):
        self.constraints = constraints

    def project(self, state: List[float], velocity: List[float], horizon: int) -> Tuple[List[float], bool]:
        projected = [x + v * horizon for x, v in zip(state, velocity)]
        valid = all(x > self.constraints.state_floor for x in projected)
        return projected, valid

class UniversalInterceptor:
    def __init__(self, constraints: ConstraintSet):
        self.constraints = constraints

    def evaluate(self, current_state: List[float], projected_state: List[float]) -> bool:
        for current, projected in zip(current_state, projected_state):
            if projected <= self.constraints.state_floor:
                return True
            if current > self.constraints.state_floor and projected < current:
                return True
        return False

class EvidenceLedger:
    """[SYS-LEDG-04] Cryptographic state logging engine."""
    def __init__(self):
        self.previous_hash = "GENESIS_UGRCK_EL_SPEI_PURIFIED_CORE_v8.0"

    def commit(self, target: TargetSystem, velocity: List[float], renewed_state: List[float]) -> str:
        payload = self.previous_hash + target.identifier + str(target.state) + str(renewed_state) + str(time.time_ns())
        current_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        self.previous_hash = current_hash
        return current_hash

# ============================================================
# 2. ENTERPRISE REST API INTERFACE
# ============================================================

class UGRCKEnterpriseServer(BaseHTTPRequestHandler):
    def _set_headers(self, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

    def do_POST(self):
        if self.path == '/api/v1/kernel/execute':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                ts_data = data['target_system']
                ctrl_data = data['control_vectors']
                
                target = TargetSystem(
                    identifier=ts_data['identifier'],
                    domain=ts_data['domain'],
                    state=ts_data['state'],
                    flows=ts_data['flows'],
                    lower_bounds=ts_data['lower_bounds'],
                    temporal_horizon=ts_data.get('temporal_horizon', 50)
                )
                
                constraints = ConstraintSet()
                if not ElSpeiHadamardGuard.validate(target.state):
                    self._set_headers(400)
                    self.wfile.write(json.dumps({
                        "status": "RED_BOLT",
                        "error": "SYS-HAD-01 BREACH: Multi-flow state coordinates must be strictly positive."
                    }).encode())
                    return
                
                total_flow = MultiFlowRouterEngine.aggregate(target.flows)
                impact_engine = GenerativeImpactVelocityEngine(constraints)
                impact = impact_engine.compute(target.state, total_flow, ctrl_data['gradient'], ctrl_data['dynamic_matrix'])
                
                trajectory_engine = PredictiveTrajectoryEngine(constraints)
                projected_state, trajectory_valid = trajectory_engine.project(target.state, impact.velocity, target.temporal_horizon)
                
                interceptor = UniversalInterceptor(constraints)
                intercepted = interceptor.evaluate(target.state, projected_state)
                
                renewed_state = [max(x, 1e-9) for x in target.state] if intercepted else [x + v for x, v in zip(target.state, impact.velocity)]
                
                ledger = EvidenceLedger()
                hash_val = ledger.commit(target, impact.velocity, renewed_state)
                
                state_res = ExecutionState.INTERCEPTED if intercepted else (ExecutionState.SYSTEM_LOCK if not trajectory_valid else ExecutionState.REGENERATING)
                
                response = {
                    "status": "success",
                    "execution_state": state_res.value,
                    "intercepted": intercepted,
                    "trajectory_valid": trajectory_valid,
                    "renewed_state": renewed_state,
                    "metrics": {"impact_velocity": impact.impact_velocity},
                    "cryptographic_proof": {"evidence_hash": hash_val}
                }
                
                self._set_headers(200)
                self.wfile.write(json.dumps(response).encode())
                
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Endpoint not found"}).encode())

def run(port=8080):
    server_address = ('', port)
    httpd = HTTPServer(server_address, UGRCKEnterpriseServer)
    print(f"[🟢 SERVER ACTIVE] UGRCK Enterprise Server listening on port {port}...")
    httpd.serve_forever()

if __name__ == '__main__':
    run()
