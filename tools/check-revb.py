#!/usr/bin/env python3
"""Independent Rev B net-contract regression check; does not prove physical hardware."""
import hashlib, json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
pins = json.loads((root / 'electronics/out/net-contract.json').read_text())
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
print('Rev B interfaces: Pi/Shrike sockets, power separation, sensors, driver PWP and coast gating passed.')
