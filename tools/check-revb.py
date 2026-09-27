#!/usr/bin/env python3
"""Independent Rev B net-contract regression check; does not prove physical hardware."""
import hashlib, heapq, json, math
from pathlib import Path

root = Path(__file__).resolve().parents[1]
pins = json.loads((root / 'electronics/out/net-contract.json').read_text())
# Physical pad order frozen from the committed Rev B contract, independent of
# generate.py and its regenerated net-contract.json.
rev_b_connectors = {
    'J1': [
        'HOST_3V3', None, None, None, None, 'H_GND', None, 'H_TX',
        'H_GND', 'H_RX', None, None, None, 'H_GND', None, None,
        'HOST_3V3', None, None, 'H_GND', None, None, None, None,
        'H_GND', None, None, None, None, 'H_GND', None, None,
        None, 'H_GND', None, None, None, None, 'H_GND', None,
    ],
    'J2': [
        None, 'BASE_3V3', 'ESTOP_RP', 'L_IN1', 'L_IN2', 'R_IN3', 'R_IN4', 'BASE_GND',
        'US_TRIG', 'US_ECHO_3V', None, None, 'BASE_GND', None, None, 'ESTOP_FPGA',
        'FPGA_PWM_L', 'FPGA_PWM_R', 'FAULT_FPGA_N',
    ],
    'J3': ['BASE_5V', 'SENSOR_TRIG', 'US_ECHO_5V', 'BASE_GND'],
    'J4': [
        None, 'BASE_3V3', 'IMU_INT', 'FAULT_RP_N', 'IMU_SCL', 'IMU_SDA', 'BASE_GND', None,
        None, 'ENC_R_B', 'ENC_R_A', 'ENC_L_B', 'BASE_GND', 'ENC_L_A', None, None,
        'RP_UART_RX', 'RP_UART_TX', 'BASE_GND',
    ],
    'J5': ['BASE_3V3', 'ESTOP_N'],
    'J6': ['BASE_5V', 'BASE_GND'],
    'J7': ['MOTOR_6V', 'BASE_GND'],
    'J8': ['MOTOR_L_P', 'MOTOR_L_N'],
    'J9': ['MOTOR_R_P', 'MOTOR_R_N'],
    'J10': ['BASE_GND', 'BASE_3V3', 'ENC_L_A', 'ENC_L_B'],
    'J11': ['BASE_GND', 'BASE_3V3', 'ENC_R_A', 'ENC_R_B'],
    'J12': ['HOST_3V3', 'H_GND', 'H_TX', 'H_RX'],
    'J13': ['BASE_GND', 'BASE_3V3', 'IMU_SDA', 'IMU_SCL', 'IMU_INT'],
}
assert {ref for ref in pins if ref.startswith('J')} == set(rev_b_connectors), 'Connector set changed'
for ref, expected_pins in rev_b_connectors.items():
    actual = pins[ref]
    assert len(actual) == len(expected_pins) and [actual[str(i)] for i in range(1, len(actual)+1)] == expected_pins, ('Changed connector pinout', ref)
assert len(pins['J1']) == 40, 'Missing Pi 40-pin socket'
for n, net in {'1':'HOST_3V3', '6':'H_GND', '8':'H_TX', '10':'H_RX'}.items():
    assert pins['J1'][n] == net, ('Pi physical pin', n)
assert pins['J1']['2'] is None and pins['J1']['4'] is None, 'Pi 5 V must remain disconnected'
assert len(pins['J2']) == len(pins['J4']) == 19, 'Missing physical Shrike rows'
assert pins['J2']['1'] is pins['J4']['1'] is None, 'Shrike USB is the sole 5 V power entry'
assert pins['J4']['14'] == 'ENC_L_A' and pins['J4']['12'] == 'ENC_L_B'
assert pins['J4']['11'] == 'ENC_R_A' and pins['J4']['10'] == 'ENC_R_B'
assert pins['J4']['6'] == 'IMU_SDA' and pins['J4']['5'] == 'IMU_SCL'
assert pins['J4']['4']=='FAULT_RP_N' and pins['J2']['19']=='FAULT_FPGA_N'
assert pins['J2']['3']=='ESTOP_RP' and pins['J2']['16']=='ESTOP_FPGA'
assert pins['U3']['8']=='DRV_FAULT_N' and pins['U3']['1']=='ESTOP_N'
assert not {'ESTOP_N','DRV_FAULT_N'} & set(pins['J2'].values())
assert not {'ESTOP_N','DRV_FAULT_N'} & set(pins['J4'].values())
buffer=['BASE_GND','ESTOP_N','ESTOP_RP_DRIVE','BASE_GND','ESTOP_N','ESTOP_FPGA_DRIVE','BASE_GND','FAULT_RP_DRIVE','DRV_FAULT_N','BASE_GND','FAULT_FPGA_DRIVE','DRV_FAULT_N','BASE_GND','BASE_3V3']
assert pins['U5']=={str(i):n for i,n in enumerate(buffer,1)}
for ref,source,destination in [('R16','ESTOP_RP_DRIVE','ESTOP_RP'),('R17','ESTOP_FPGA_DRIVE','ESTOP_FPGA'),('R18','FAULT_RP_DRIVE','FAULT_RP_N'),('R19','FAULT_FPGA_DRIVE','FAULT_FPGA_N')]:
    assert pins[ref]=={'1':source,'2':destination}
# TI DRV8833 PWP (not RTY) physical pad order, including exposed pad 17.
expected = ['ESTOP_N','MOTOR_L_P','SENSE_L','MOTOR_L_N','MOTOR_R_N',
            'SENSE_R','MOTOR_R_P','DRV_FAULT_N','DRV_BIN1','DRV_BIN2',
            'DRV_VCP','MOTOR_6V','BASE_GND','DRV_VINT','DRV_AIN2','DRV_AIN1','BASE_GND']
assert pins['U3'] == {str(i): n for i,n in enumerate(expected,1)}, 'Driver PWP pinout'
for ref in ('R7','R8'):
    assert pins[ref]['2'] == 'BASE_GND', 'Sense resistor return'
assert pins['J3'] == {'1':'BASE_5V','2':'SENSOR_TRIG','3':'US_ECHO_5V','4':'BASE_GND'}
# Check the actual quad-AND wiring against the TI pin grouping, then its coast state.
for a,b,y,signal,pwm,output in [(1,2,3,'L_IN1','FPGA_PWM_L','DRV_AIN1'),(4,5,6,'L_IN2','FPGA_PWM_L','DRV_AIN2'),(9,10,8,'R_IN3','FPGA_PWM_R','DRV_BIN1'),(12,13,11,'R_IN4','FPGA_PWM_R','DRV_BIN2')]:
    assert [pins['U4'][str(p)] for p in (a,b,y)] == [signal,pwm,output]
geometry=json.loads((root/'electronics/out/pad-geometry.json').read_text())
assert geometry['board_sha256']==hashlib.sha256((root/'electronics/carrier.kicad_pcb').read_bytes()).hexdigest(), 'Stale pad geometry'
fp=geometry['footprints']
assert fp['J1']['side']=='B.Cu' and fp['J2']['side']==fp['J4']['side']=='F.Cu'
for ref,part in pins.items():
    for number,net in part.items():
        actual=fp[ref]['pins'][number]['net']
        assert actual==net if net else actual.startswith('unconnected-'), (ref,number,actual,net)
# Independent official Pi STEP datum, retained in top-view PCB coordinates.
for i in range(20):
    for n,y in [(2*i+1,24.77),(2*i+2,22.23)]:
        p=fp['J1']['pins'][str(n)]
        assert abs(p['x']-(8.37+2.54*i))<1e-5 and abs(p['y']-y)<1e-5, ('Pi physical datum',n)
for ref,x,y in [('J2',100.27,21.0958),('J4',123.13,21.121)]:
    for i in range(19):
        p=fp[ref]['pins'][str(i+1)]
        assert abs(p['x']-x)<1e-5 and abs(p['y']-(y+2.54*i))<1e-5
        assert abs(p['drill']-1.02)<1e-5, 'Samtec socket drill'
for n,(x,y) in enumerate([(3.5,23.5),(61.5,23.5),(3.5,72.5),(61.5,72.5)],5):
    assert (fp[f'H{n}']['x'],fp[f'H{n}']['y'])==(x,y)
    assert fp[f'H{n}']['hole_drill']==2.7, 'Pi M2.5 hole clearance'
# Frozen Rev B connector placements: B.1 is a drop-in layout revision.
for ref,x,y,angle in [('J3',84,91,0),('J5',86,8,0),('J6',110,91,0),('J7',149,86,0),('J8',151,59,90),('J9',151,43,90),('J10',128,8,0),('J11',143,13,0),('J12',18,11,0),('J13',135,22,0)]:
    assert (fp[ref]['x'],fp[ref]['y'],fp[ref]['angle'])==(x,y,angle), ('Moved connector',ref)
for i,(x,y) in enumerate([(5,5),(155,5),(155,95),(5,95)],1):
    assert (fp[f'H{i}']['x'],fp[f'H{i}']['y'],fp[f'H{i}']['hole_drill'])==(x,y,3.2)
edges=geometry['edges']
assert len(edges)==12 and sum(e['shape']=='Arc' for e in edges)==4, 'Board/cooler outline changed'
expected_edges={tuple(sorted((a,z))) for a,z in [((0,0),(160,0)),((160,0),(160,100)),((160,100),(0,100)),((0,100),(0,0)),((10,32),(66,32)),((68,34),(68,64)),((66,66),(10,66)),((8,64),(8,34))]}
assert {tuple(sorted((tuple(e['start']),tuple(e['end'])))) for e in edges if e['shape']!='Arc'}==expected_edges
arc_geometry=[((66,32),(68,34),(67.414214,32.585786)),((68,64),(66,66),(67.414214,65.414214)),((10,66),(8,64),(8.585786,65.414214)),((8,34),(10,32),(8.585786,32.585786))]
for e in edges:
    if e['shape']=='Arc':
        assert any({tuple(e['start']),tuple(e['end'])}=={a,z} and math.dist(e['mid'],mid)<1e-5 for a,z,mid in arc_geometry), 'Cooler corner radius changed'
assert len(fp['U3']['thermal_vias'])==12 and all(p['net']=='BASE_GND' and p['drill']==.2 for p in fp['U3']['thermal_vias'])
for ref in ('J1','J2','J3','J4','J6','J10','J11','J12','J13'):
    assert all(p['thermal_relief'] for p in fp[ref]['pins'].values() if p['net'] in ('H_GND','BASE_GND')), ('Hand solder relief',ref)
assert not fp['J7']['pins']['2']['thermal_relief'], 'Motor return must retain direct copper'
for i,net in enumerate(['HOST_3V3','H_GND','BASE_3V3','BASE_5V','MOTOR_6V','BASE_GND','ESTOP_N','DRV_FAULT_N','SENSE_L','SENSE_R'],1):
    ref=f'TP{i}'; p=fp[ref]
    assert p['side']=='F.Cu' and p['pins']['1']['net']==net and pins[ref]=={'1':net}, ('Probe net',ref)
    # Include a 2 mm probe radius around the installed Shrike/module/socket envelope.
    assert not (97<p['x']<126.4 and 8<p['y']<70.5), ('Probe hidden by Shrike',ref)
    assert p['x']<73 if net in ('HOST_3V3','H_GND') else p['x']>77, ('Probe crosses isolation barrier',ref)
assert {r for r in fp if r.startswith('FID')}=={'FID1','FID2','FID3'}
fid=[(fp[f'FID{i}']['x'],fp[f'FID{i}']['y']) for i in range(1,4)]
assert abs((fid[1][0]-fid[0][0])*(fid[2][1]-fid[0][1])-(fid[1][1]-fid[0][1])*(fid[2][0]-fid[0][0]))>100, 'Collinear fiducials'

for t in geometry['tracks']:
    xs=[t['start'][0],t['end'][0]]
    if t['net']=='H_GND': assert max(xs)+t['width']/2<74, 'Host return crosses barrier'
    if t['net']=='BASE_GND': assert min(xs)-t['width']/2>76, 'Base return crosses barrier'

def route_length(net,start,end):
    """Shortest top-copper pad-centre path; probe branches must not inflate it."""
    graph={}
    for t in geometry['tracks']:
        if t['net']!=net or t['layer']!='F.Cu': continue
        # KiCad DSN round trips can differ by 1 nm at shared pad/track endpoints.
        a,z=(tuple(round(c,4) for c in t[p]) for p in ('start','end')); length=math.dist(a,z)
        graph.setdefault(a,[]).append((z,length)); graph.setdefault(z,[]).append((a,length))
    queue=[(0,start)]; best={start:0}
    while queue:
        dist,node=heapq.heappop(queue)
        if dist>best[node]: continue
        if node==end: return dist
        for nxt,length in graph.get(node,[]):
            score=dist+length
            if score<best.get(nxt,math.inf): best[nxt]=score; heapq.heappush(queue,(score,nxt))
    raise AssertionError(('No continuous local F.Cu path',net,start,end))

for net,pin,ref,limit in [('SENSE_L','3','R7',7),('SENSE_R','6','R8',7),('MOTOR_6V','12','C5',4),('DRV_VINT','14','C7',4),('DRV_VCP','11','C6',3)]:
    def pos(ref,pin): return tuple(round(fp[ref]['pins'][pin][a],4) for a in ('x','y'))
    length=route_length(net,pos('U3',pin),pos(ref,'1'))
    assert length<=limit+.001, (net,length,limit)
    print(f'{net}: {length:.3f} mm (target <= {limit} mm)')
print('Rev B.1 interfaces, local routes, test pads, fiducials and assembly features passed.')
