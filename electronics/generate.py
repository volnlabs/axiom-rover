#!/usr/bin/env python3
"""Generate review-revision carrier source with KiCad's bundled pcbnew Python.
Re-running replaces CAD edits: use generated KiCad files directly for manual revision.
"""
import argparse, csv, json, os, uuid, shutil, math, re
from pathlib import Path
import pcbnew as k

ROOT = Path(__file__).resolve().parent
UID = lambda s: str(uuid.uuid5(uuid.NAMESPACE_URL, 'volnlabs/axiom-rover/carrier/'+s))
SHEET = UID('sheet')
def xh(n): return f'Connector_JST:JST_XH_B{n}B-XH-A_1x{n:02d}_P2.50mm_Vertical'
R = 'Resistor_SMD:R_0805_2012Metric'
C = 'Capacitor_SMD:C_0805_2012Metric'
# ref, value, footprint, physical-pad-ordered nets, PCB x/y/angle, schematic x/y
# J1 is fitted BELOW the PCB; its pad numbers are stated in top-board coordinates.
PI_NETS=[None]*40
for pin,net in {1:'HOST_3V3',17:'HOST_3V3',6:'H_GND',9:'H_GND',14:'H_GND',20:'H_GND',25:'H_GND',30:'H_GND',34:'H_GND',39:'H_GND',8:'H_TX',10:'H_RX'}.items(): PI_NETS[pin-1]=net
SENSOR_FP=lambda n: xh(n)
POWER_FP='Connector_JST:JST_VH_B2P-VH_1x02_P3.96mm_Vertical'
DRV_FP='Package_SO:HTSSOP-16-1EP_4.4x5mm_P0.65mm_EP3.4x5mm_Mask2.46x2.31mm_ThermalVias'
PARTS=[
('J1','ESQ-120-24-G-D_PI5_BOTTOM','Rover:Pi5_Socket_2x20',PI_NETS,(0,20,0),(70,100)),
('J2','SHRIKE_J2_SSW-119-01-G-S','Rover:SSW-119-01-G-S',[None,'BASE_3V3','ESTOP_RP','L_IN1','L_IN2','R_IN3','R_IN4','BASE_GND','US_TRIG','US_ECHO_3V',None,None,'BASE_GND',None,None,'ESTOP_FPGA','FPGA_PWM_L','FPGA_PWM_R','FAULT_FPGA_N'],(100.27,21.0958,0),(245,100)),
('J4','SHRIKE_J4_SSW-119-01-G-S','Rover:SSW-119-01-G-S',[None,'BASE_3V3','IMU_INT','FAULT_RP_N','IMU_SCL','IMU_SDA','BASE_GND',None,None,'ENC_R_B','ENC_R_A','ENC_L_B','BASE_GND','ENC_L_A',None,None,'RP_UART_RX','RP_UART_TX','BASE_GND'],(123.13,21.121,0),(420,100)),
('U3','DRV8833PWPR',DRV_FP,['ESTOP_N','MOTOR_L_P','SENSE_L','MOTOR_L_N','MOTOR_R_N','SENSE_R','MOTOR_R_P','DRV_FAULT_N','DRV_BIN1','DRV_BIN2','DRV_VCP','MOTOR_6V','BASE_GND','DRV_VINT','DRV_AIN2','DRV_AIN1','BASE_GND'],(123,79,0),(595,100)),
('U4','SN74LVC08ADR','Package_SO:SOIC-14_3.9x8.7mm_P1.27mm',['L_IN1','FPGA_PWM_L','DRV_AIN1','L_IN2','FPGA_PWM_L','DRV_AIN2','BASE_GND','DRV_BIN1','R_IN3','FPGA_PWM_R','DRV_BIN2','R_IN4','FPGA_PWM_R','BASE_3V3'],(137,45,0),(770,100)),
('U1','ISO7721DR','Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',['HOST_3V3','H_RX','H_TX','H_GND','BASE_GND','RP_UART_RX','RP_UART_TX','BASE_3V3'],(75,15,0),(945,100)),
('C1','100nF 16V X7R',C,['HOST_3V3','H_GND'],(69,15,-90),(0,0)),
('C2','100nF 16V X7R',C,['BASE_3V3','BASE_GND'],(81,15,-90),(0,0)),
('J3','HC_SR04_VCC_TRIG_ECHO_GND',SENSOR_FP(4),['BASE_5V','SENSOR_TRIG','US_ECHO_5V','BASE_GND'],(84,91,0),(0,0)),
('R1','1k 1%',R,['US_TRIG','SENSOR_TRIG'],(86,76,0),(0,0)),
('R2','2.2k 1%',R,['US_ECHO_5V','ECHO_DIV'],(91,81,0),(0,0)),
('R3','3.3k 1%',R,['ECHO_DIV','BASE_GND'],(85,81,0),(0,0)),
('U2','SN74LVC1G17DBVR','Package_TO_SOT_SMD:SOT-23-5',[None,'ECHO_DIV','BASE_GND','US_ECHO_3V','BASE_3V3'],(91,75,0),(0,0)),
('C3','100nF 16V X7R',C,['BASE_3V3','BASE_GND'],(95,75,90),(0,0)),
('R4','10k 1%',R,['ESTOP_N','BASE_GND'],(95,14,90),(0,0)),
('R5','10k 1%',R,['FPGA_PWM_L','BASE_GND'],(136,55,0),(0,0)),
('R6','10k 1%',R,['FPGA_PWM_R','BASE_GND'],(136,58,0),(0,0)),
('R7','0.20R 1W CSRT1206FTR200','Resistor_SMD:R_1206_3216Metric',['SENSE_L','BASE_GND'],(110,73,0),(0,0)),
('R8','0.20R 1W CSRT1206FTR200','Resistor_SMD:R_1206_3216Metric',['SENSE_R','BASE_GND'],(110,85,0),(0,0)),
('R9','10k 1%',R,['DRV_FAULT_N','BASE_3V3'],(133,64,0),(0,0)),
('R10','10k 1%',R,['L_IN1','BASE_GND'],(88,32,0),(0,0)),
('R11','10k 1%',R,['L_IN2','BASE_GND'],(88,35,0),(0,0)),
('R12','10k 1%',R,['R_IN3','BASE_GND'],(88,38,0),(0,0)),
('R13','10k 1%',R,['R_IN4','BASE_GND'],(88,41,0),(0,0)),
('C4','100nF 16V X7R',C,['BASE_3V3','BASE_GND'],(141,38,0),(0,0)),
('C5','10uF 16V X7R','Capacitor_SMD:C_1206_3216Metric',['MOTOR_6V','BASE_GND'],(131,77,0),(0,0)),
('C6','10nF 25V X7R',C,['DRV_VCP','MOTOR_6V'],(131,80,0),(0,0)),
('C7','2.2uF 16V X7R',C,['DRV_VINT','BASE_GND'],(129,74,0),(0,0)),
('C8','470uF 16V','Capacitor_THT:CP_Radial_D8.0mm_P3.50mm',['MOTOR_6V','BASE_GND'],(126,89,0),(0,0)),
('D1','SMBJ6.0A','Diode_SMD:D_SMB',['MOTOR_6V','BASE_GND'],(138,90,0),(0,0)),
('J5','ESTOP_LOGIC_NC',xh(2),['BASE_3V3','ESTOP_N'],(86,8,0),(0,0)),
('J6','BASE_SENSOR_5V_IN',xh(2),['BASE_5V','BASE_GND'],(110,91,0),(0,0)),
('J7','6V_AFTER_FUSE_AND_STOP_RELAY',POWER_FP,['MOTOR_6V','BASE_GND'],(149,86,0),(0,0)),
('J8','LEFT_MOTOR',POWER_FP,['MOTOR_L_P','MOTOR_L_N'],(151,59,90),(0,0)),
('J9','RIGHT_MOTOR',POWER_FP,['MOTOR_R_P','MOTOR_R_N'],(151,43,90),(0,0)),
('J10','ENCODER_LEFT_3V3',SENSOR_FP(4),['BASE_GND','BASE_3V3','ENC_L_A','ENC_L_B'],(128,8,0),(0,0)),
('J11','ENCODER_RIGHT_3V3',SENSOR_FP(4),['BASE_GND','BASE_3V3','ENC_R_A','ENC_R_B'],(143,13,0),(0,0)),
('J12','ALTERNATE_HOST_UART',xh(4),['HOST_3V3','H_GND','H_TX','H_RX'],(18,11,0),(0,0)),
('J13','IMU_3V3_I2C_INT',SENSOR_FP(5),['BASE_GND','BASE_3V3','IMU_SDA','IMU_SCL','IMU_INT'],(135,22,0),(0,0)),
('R14','4.7k 1%',R,['IMU_SDA','BASE_3V3'],(133,30,0),(0,0)),
('R15','4.7k 1%',R,['IMU_SCL','BASE_3V3'],(140,30,0),(0,0)),
('U5','SN74LVC125ADR','Package_SO:SOIC-14_3.9x8.7mm_P1.27mm',['BASE_GND','ESTOP_N','ESTOP_RP_DRIVE','BASE_GND','ESTOP_N','ESTOP_FPGA_DRIVE','BASE_GND','FAULT_RP_DRIVE','DRV_FAULT_N','BASE_GND','FAULT_FPGA_DRIVE','DRV_FAULT_N','BASE_GND','BASE_3V3'],(87,56,0),(0,0)),
('C9','100nF 16V X7R',C,['BASE_3V3','BASE_GND'],(94,56,0),(0,0)),
('R16','1k 1%',R,['ESTOP_RP_DRIVE','ESTOP_RP'],(94,47,0),(0,0)),
('R17','1k 1%',R,['ESTOP_FPGA_DRIVE','ESTOP_FPGA'],(94,51,0),(0,0)),
('R18','1k 1%',R,['FAULT_RP_DRIVE','FAULT_RP_N'],(94,61,0),(0,0)),
('R19','1k 1%',R,['FAULT_FPGA_DRIVE','FAULT_FPGA_N'],(94,65,0),(0,0)),
]
# Distribute the remaining small blocks on one legible A0 electrical sheet.
PARTS=[p[:-1]+((70+(i-6)%6*175,225+(i-6)//6*75),) if i>=6 else p for i,p in enumerate(PARTS)]
MOTOR_NETS={'MOTOR_6V','MOTOR_L_P','MOTOR_L_N','MOTOR_R_P','MOTOR_R_N','SENSE_L','SENSE_R'}
BOARD_W,BOARD_H=160,100
PI_HOLES=[(3.5,23.5),(61.5,23.5),(3.5,72.5),(61.5,72.5)]

def socket_footprints():
    """Samtec body/drill dimensions; Pi pin centres from official RP-010083-CA STEP.
    1.8 mm copper pads are our annular-ring choice, not a Samtec dimension.
    """
    local=ROOT/'Rover.pretty'; local.mkdir(exist_ok=True)
    for name,side,pads,box in [
        ('SSW-119-01-G-S','F',[(i+1,0,2.54*i) for i in range(19)],(-1.205,-1.525,1.205,47.245)),
        ('Pi5_Socket_2x20','B',[(2*i+j,8.37+2.54*i,4.77 if j==1 else 2.23) for i in range(20) for j in (1,2)],(6.845,1.025,58.155,5.975))]:
        x1,y1,x2,y2=box
        s=[f'(footprint "{name}" (version 20241229) (generator "rover_generator") (layer "{side}.Cu") (attr through_hole)',f'(fp_text reference "REF**" (at 0 -3) (layer "{side}.SilkS") (effects (font (size 1 1) (thickness .15))))',f'(fp_text value "{name}" (at 0 -5) (layer "{side}.Fab") (effects (font (size 1 1) (thickness .15))))']
        for layer,margin,width in [('Fab',0,.1),('CrtYd',.5,.05)]:
            s.append(f'(fp_rect (start {x1-margin} {y1-margin}) (end {x2+margin} {y2+margin}) (stroke (width {width}) (type default)) (fill none) (layer "{side}.{layer}"))')
        for n,x,y in pads: s.append(f'(pad "{n}" thru_hole {"rect" if n==1 else "circle"} (at {x} {y}) (size 1.8 1.8) (drill 1.02) (layers "*.Cu" "*.Mask"))')
        s.append(')'); (local/(name+'.kicad_mod')).write_text('\n'.join(s)+'\n')

def pin_info(ref,n,net):
    if ref=='D1': return ('K','A')[n-1],'passive',-1,0
    if ref=='J1':
        return str(n),'passive',-1 if n%2 else 1,(9.5-(n-1)//2)*5.08
    if ref=='U1':
        names=['VCC1','OUTA','INB','GND1','GND2','OUTB','INA','VCC2']
        types=['power_in','output','input','power_in','power_in','output','input','power_in']
        side=-1 if n<=4 else 1
        return names[n-1],types[n-1],side,((2.5-n) if n<=4 else (n-6.5))*5.08
    if ref=='U2':
        names=['NC','A','GND','Y','VCC']; types=['no_connect','input','power_in','output','power_in']
        return names[n-1],types[n-1],-1,(3-n)*5.08
    if ref=='U3':
        names=['nSLEEP','AOUT1','AISEN','AOUT2','BOUT2','BISEN','BOUT1','nFAULT','BIN1','BIN2','VCP','VM','GND','VINT','AIN2','AIN1','EP']
        types=['input','output','passive','output','output','passive','output','open_collector','input','input','passive','power_in','power_in','power_out','input','input','power_in']
        return names[n-1],types[n-1],-1 if n<=8 else 1,(4.5-n)*5.08 if n<=8 else (n-13)*5.08
    if ref=='U5':
        names=['1OE_N','1A','1Y','2OE_N','2A','2Y','GND','3Y','3A','3OE_N','4Y','4A','4OE_N','VCC']
        typ='power_in' if n in (7,14) else 'output' if n in (3,6,8,11) else 'input'
        return names[n-1],typ,-1 if n<=7 else 1,(4-n)*5.08 if n<=7 else (n-11)*5.08
    if ref=='U4':
        names=['1A','1B','1Y','2A','2B','2Y','GND','3Y','3A','3B','4Y','4A','4B','VCC']
        typ='power_in' if n in (7,14) else 'output' if n in (3,6,8,11) else 'input'
        return names[n-1],typ,-1 if n<=7 else 1,(4-n)*5.08 if n<=7 else (n-11)*5.08
    return str(n),'passive',-1,0 # assigned spacing below

def schematic():
    libs=[]; items=[]
    for ref,val,fp,nets,place,(x,y) in PARTS:
        x=round(x/1.27)*1.27; y=round(y/1.27)*1.27
        name=ref; half=max(7.62,(len(nets)+1)*2.54) if not ref.startswith('U') else max(15.24,(len(nets)//2+1)*2.54)
        if ref=='J1': half=53.34
        if ref[0] in "RC": half=3.81
        pins=[]; pdata=[]
        for n,net in enumerate(nets,1):
            label,typ,side,dy=pin_info(ref,n,net)
            if not ref.startswith('U') and ref!='J1': dy=((len(nets)+1)/2-n)*5.08
            if ref[0] in "RC": side=-1 if n==1 else 1; dy=0
            px=side*(7.62 if ref[0] in 'RC' else 15.24); ang=0 if side<0 else 180
            length=(6.35 if ref[0]=='C' else 5.08)
            pins.append(f'(pin {typ} line (at {px} {dy} {ang}) (length {length}) (name "{label}" (effects (font (size 1.0 1.0)))) (number "{n}" (effects (font (size 1.0 1.0)))))')
            pdata.append((n,net,x+px,y-dy,side))
        graphic=f'(rectangle (start -10.16 {half}) (end 10.16 {-half}) (stroke (width 0.254) (type default)) (fill (type background)))'
        if ref[0]=='R': graphic='(rectangle (start -2.54 1.27) (end 2.54 -1.27) (stroke (width 0.254) (type default)) (fill (type none)))'
        if ref[0]=='C': graphic=''.join(f'(polyline (pts (xy {a} -2.54) (xy {a} 2.54)) (stroke (width 0.254) (type default)) (fill (type none)))' for a in (-1.27,1.27))
        if ref=='C8': graphic+='(text "+" (at -3 3.5 0) (effects (font (size 1.5 1.5))))'
        libs.append(f'''(symbol "Rover:{name}" (pin_names (offset 0.8) {"hide" if ref[0] in "RC" else ""}) {"(pin_numbers hide)" if ref[0] in "RC" else ""} (in_bom yes) (on_board yes)
          (property "Reference" "{ref}" (at 0 {half+5.08} 0) (effects (font (size 1.27 1.27))))
          (property "Value" "{val}" (at 0 {half+2.54} 0) (effects (font (size 1.27 1.27))))
          (property "Footprint" "{fp}" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
          (symbol "{name}_0_1" {graphic})
          (symbol "{name}_1_1" {''.join(pins)}))''')
        items.append(f'''(symbol (lib_id "Rover:{name}") (at {x} {y} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid "{UID(ref)}")
          (property "Reference" "{ref}" (at {x} {y-half-5.08} 0) (effects (font (size 1.27 1.27))))
          (property "Value" "{val}" (at {x} {y-half-2.54} 0) (effects (font (size 1.27 1.27))))
          (property "Footprint" "{fp}" (at {x} {y} 0) (effects (font (size 1.27 1.27)) hide))
          {''.join(f'(pin "{n}" (uuid "{UID(ref+str(n))}"))' for n in range(1,len(nets)+1))}
          (instances (project "carrier" (path "/{SHEET}" (reference "{ref}") (unit 1)))))''')
        for n,net,px,py,side in pdata:
            if net is None:
                items.append(f'(no_connect (at {px} {py}) (uuid "{UID(ref+str(n)+"nc")}"))'); continue
            ex=px+side*5.08
            items.append(f'(wire (pts (xy {px} {py}) (xy {ex} {py})) (stroke (width 0) (type default)) (uuid "{UID(ref+str(n)+"wire")}"))')
            items.append(f'(label "{net}" (at {ex} {py} 0) (effects (font (size 1 1)) (justify {"right" if side<0 else "left"} bottom)) (uuid "{UID(ref+str(n)+"label")}"))')
    # Explicit off-board rail sources; power_out only on power-entry flags.
    libs.append('''(symbol "Rover:PWR_FLAG" (power) (pin_names (offset 0)) (in_bom no) (on_board no)
      (property "Reference" "#FLG" (at 0 3 0) (effects (font (size 1 1)) hide))
      (property "Value" "PWR_FLAG" (at 0 5 0) (effects (font (size 1 1))))
      (symbol "PWR_FLAG_0_1" (polyline (pts (xy -1 2) (xy 0 3) (xy 1 2) (xy 0 1) (xy -1 2)) (stroke (width 0.2) (type default)) (fill (type none))))
      (symbol "PWR_FLAG_1_1" (pin power_out line (at 0 0 90) (length 1) (name "pwr" (effects (font (size 1 1)))) (number "1" (effects (font (size 1 1)))))))''')
    for i,net in enumerate(['HOST_3V3','H_GND','BASE_3V3','BASE_GND','BASE_5V','MOTOR_6V']):
        x=round((70+i*175)/1.27)*1.27; y=round(740/1.27)*1.27; ref=f'#FLG0{i+1}'
        items.append(f'''(symbol (lib_id "Rover:PWR_FLAG") (at {x} {y} 0) (unit 1) (in_bom no) (on_board no) (uuid "{UID(ref)}")
          (property "Reference" "{ref}" (at {x} {y-3} 0) (effects (font (size 1 1)) hide))
          (property "Value" "OFFBOARD RAIL" (at {x} {y-5} 0) (effects (font (size 1 1))))
          (pin "1" (uuid "{UID(ref+'pin')}"))
          (instances (project "carrier" (path "/{SHEET}" (reference "{ref}") (unit 1)))))
          (label "{net}" (at {x} {y} 0) (effects (font (size 1 1)) (justify left bottom)) (uuid "{UID(ref+'label')}"))''')
    for i,(txt,x,y) in enumerate([
        ('REV B: Pi 5 bottom socket + Shrike R0.4 top sockets; no host/base ground tie',550,20),
        ('J7: REGULATED 6 V AFTER EXTERNAL FUSE + INDEPENDENT STOP RELAY. 1 A nominal per motor.',550,765),
        ('FPGA PWM gates direction inputs through U4. nSLEEP is STOP level, never PWM.',550,775),
        ('Shrike USB-C is sole 5 V power entry. J1 pins 2/4 and J2/J4 pin 1 stay disconnected.',550,785),
        ('REVIEW ONLY: physical fit, current limit, cooling and firmware timing require bench evidence.',550,795)]):
        items.append(f'(text "{txt}" (at {x} {y} 0) (effects (font (size 1.27 1.27))) (uuid "{UID("note"+str(i))}"))')
    (ROOT/'carrier.kicad_sch').write_text(f'(kicad_sch (version 20250114) (generator "rover_generator") (uuid "{SHEET}") (paper "A0") (title_block (title "Axiom Rover — Pi 5 / Shrike socket carrier") (date "2026-09-09") (rev "B REVIEW")) (lib_symbols {"".join(libs)}) {"".join(items)} (sheet_instances (path "/" (page "1"))))\n')
    (ROOT/'Rover.kicad_sym').write_text('(kicad_symbol_lib (version 20241209) (generator "rover_generator") '+''.join(s.replace('"Rover:','"',1) for s in libs)+')\n')
    (ROOT/'sym-lib-table').write_text('(sym_lib_table (lib (name "Rover") (type "KiCad") (uri "${KIPRJMOD}/Rover.kicad_sym") (options "") (descr "Carrier review symbols")))\n')

    # Keep schematic footprint identifiers consistent with the embedded board library.
    for file in ['carrier.kicad_sch','Rover.kicad_sym']:
        p=ROOT/file; s=p.read_text()
        for part in PARTS: s=s.replace(part[2],'Rover:'+part[2].split(':')[1])
        p.write_text(s)

def board():
    b=k.BOARD(); b.SetCopperLayerCount(2)
    settings=b.GetDesignSettings(); nc=settings.m_NetSettings.GetDefaultNetclass(); nc.SetClearance(k.FromMM(.18)); nc.SetTrackWidth(k.FromMM(.25)); nc.SetViaDiameter(k.FromMM(.7)); nc.SetViaDrill(k.FromMM(.3)); settings.SetBoardThickness(k.FromMM(1.6))
    settings.m_MinClearance=k.FromMM(.18); settings.m_TrackMinWidth=k.FromMM(.2)
    settings.m_ViasMinSize=k.FromMM(.45); settings.m_MinThroughDrill=k.FromMM(.2)
    motor=k.NETCLASS('Motor'); motor.SetClearance(k.FromMM(.2)); motor.SetTrackWidth(k.FromMM(.8)); motor.SetViaDiameter(k.FromMM(1.2)); motor.SetViaDrill(k.FromMM(.6))
    settings.m_NetSettings.SetNetclass('Motor',motor)
    for name in MOTOR_NETS: settings.m_NetSettings.SetNetclassPatternAssignment('/'+name,'Motor')
    nets={}
    for name in sorted({n for p in PARTS for n in p[3] if n}):
        net=k.NETINFO_ITEM(b,"/"+name); b.Add(net); nets[name]=net
    libroot=Path(os.environ.get('KICAD10_FOOTPRINT_DIR',str(Path(os.environ.get('APPDIR','/usr'))/'share/kicad/footprints')))
    local=ROOT/'Rover.pretty'; local.mkdir(exist_ok=True)
    def footprint(libid,ref,val,x,y,angle):
        lib,name=libid.split(':'); source=local if lib=='Rover' else libroot/(lib+'.pretty')
        fp=k.FootprintLoad(str(source),name)
        if fp is None: raise RuntimeError(f'Missing footprint: {libid}')
        if lib!='Rover': shutil.copyfile(source/(name+".kicad_mod"), local/(name+".kicad_mod"))
        fp.SetFPID(k.LIB_ID('Rover',name)); fp.SetReference(ref); fp.SetValue(val)
        fp.SetPosition(k.VECTOR2I(k.FromMM(x),k.FromMM(y))); fp.SetOrientationDegrees(angle)
        fp.Value().SetVisible(False); fp.Reference().SetTextSize(k.VECTOR2I(k.FromMM(1),k.FromMM(1))); fp.Reference().SetTextThickness(k.FromMM(.15))
        if ref.startswith('J'): fp.Reference().SetLayer(k.B_Fab if ref=='J1' else k.F_Fab)
        if ref=='J1': fp.Reference().SetMirrored(True)
        if ref=='C8': fp.Reference().SetPosition(k.VECTOR2I(k.FromMM(121),k.FromMM(89)))
        if ref=='U3': fp.Reference().SetPosition(k.VECTOR2I(k.FromMM(123),k.FromMM(74.5)))
        if ref in ('R10','R11','R12','R13','R5','R6','C3','C4','C5','C6','C7'):
            fp.Reference().SetPosition(k.VECTOR2I(k.FromMM(x+(3.5 if ref.startswith('C') else -4)),k.FromMM(y)))
            fp.Reference().SetTextAngle(k.EDA_ANGLE(0,k.DEGREES_T))
        b.Add(fp); return fp
    for ref,val,libid,pinnets,(x,y,angle),sch in PARTS:
        fp=footprint(libid,ref,val,x,y,angle)
        fp.SetPath(k.KIID_PATH('/'+SHEET+'/'+UID(ref)))
        for pad in fp.Pads():
            if not pad.GetNumber(): continue # paste-only aperture pads
            n=int(pad.GetNumber()); net=pinnets[n-1]
            if net: pad.SetNet(nets[net])
            else:
                ncname=f'unconnected-({ref}-'+('NC-' if ref=='U2' else '')+f'Pad{n})'
                ncnet=k.NETINFO_ITEM(b,ncname); b.Add(ncnet); pad.SetNet(ncnet)
    # Explicit 0.30 mm breakout necks clear the 0.65 mm driver pitch;
    # 0.8 mm motor trunks begin at 1.2/0.6 mm through-vias.
    def trace(net,a,z,width=.3,layer=k.F_Cu):
        t=k.PCB_TRACK(b); t.SetLocked(True); t.SetNet(nets[net]); t.SetLayer(layer); t.SetWidth(k.FromMM(width))
        t.SetStart(k.VECTOR2I(k.FromMM(a[0]),k.FromMM(a[1]))); t.SetEnd(k.VECTOR2I(k.FromMM(z[0]),k.FromMM(z[1]))); b.Add(t)
    for net,y,vx,vy in [('MOTOR_L_P',77.375,118,76.375),('SENSE_L',78.025,115.8,77.025),('MOTOR_L_N',78.675,113.6,77.675),('MOTOR_R_N',79.325,113.6,80.325),('SENSE_R',79.975,115.8,80.975),('MOTOR_R_P',80.625,118,81.625)]:
        trace(net,(120.1375,y),(vx+1,y)); trace(net,(vx+1,y),(vx,vy))
        via=k.PCB_VIA(b); via.SetLocked(True); via.SetNet(nets[net]); via.SetPosition(k.VECTOR2I(k.FromMM(vx),k.FromMM(vy))); via.SetWidth(k.FromMM(1.2)); via.SetDrill(k.FromMM(.6)); via.SetLayerPair(k.F_Cu,k.B_Cu); b.Add(via)
    trace('MOTOR_6V',(125.8625,79.325),(127.4,79.325))
    trace('MOTOR_6V',(127.4,79.325),(129.525,77))
    trace('DRV_VCP',(125.8625,79.975),(130.05,80),.25)
    trace('DRV_VINT',(125.8625,78.025),(127.1,78.025),.25)
    trace('DRV_VINT',(127.1,78.025),(128.05,77.075),.25)
    trace('DRV_VINT',(128.05,77.075),(128.05,74),.25)
    for net,points in [('DRV_BIN2',[(125.8625,80.625),(127.4,80.625),(128,80.75)]),('DRV_BIN2',[(139.475,45),(141,45)])]:
        for a,z in zip(points,points[1:]): trace(net,a,z,.25)
        vx,vy=points[-1]; via=k.PCB_VIA(b);via.SetLocked(True);via.SetNet(nets[net]);via.SetPosition(k.VECTOR2I(k.FromMM(vx),k.FromMM(vy)));via.SetWidth(k.FromMM(.7));via.SetDrill(k.FromMM(.3));via.SetLayerPair(k.F_Cu,k.B_Cu);b.Add(via)
    trace('MOTOR_R_N',(113.6,80.325),(113.6,83.5),.8,k.B_Cu)
    trace('MOTOR_R_N',(113.6,83.5),(118,87.9),.8,k.B_Cu)
    trace('MOTOR_R_N',(118,87.9),(118,91),.8,k.B_Cu)
    via=k.PCB_VIA(b);via.SetLocked(True);via.SetNet(nets['MOTOR_R_N']);via.SetPosition(k.VECTOR2I(k.FromMM(118),k.FromMM(91)));via.SetWidth(k.FromMM(1.2));via.SetDrill(k.FromMM(.6));via.SetLayerPair(k.F_Cu,k.B_Cu);b.Add(via)
    for i,(x,y) in enumerate([(5,5),(155,5),(155,95),(5,95)]+PI_HOLES,1):
        fp=footprint('MountingHole:MountingHole_3.2mm_M3' if i<=4 else 'MountingHole:MountingHole_2.7mm_M2.5',f'H{i}','M3 NPTH' if i<=4 else 'M2.5 NPTH',x,y,0)
        fp.SetAttributes(k.FP_BOARD_ONLY|k.FP_EXCLUDE_FROM_BOM|k.FP_EXCLUDE_FROM_POS_FILES)
        fp.Reference().SetVisible(False)
    def edge_line(a,z):
        edge=k.PCB_SHAPE(); edge.SetShape(k.SHAPE_T_SEGMENT); edge.SetStart(k.VECTOR2I(k.FromMM(a[0]),k.FromMM(a[1]))); edge.SetEnd(k.VECTOR2I(k.FromMM(z[0]),k.FromMM(z[1]))); edge.SetLayer(k.Edge_Cuts); edge.SetWidth(k.FromMM(.05)); b.Add(edge)
    for a,z in [((0,0),(160,0)),((160,0),(160,100)),((160,100),(0,100)),((0,100),(0,0)),((10,32),(66,32)),((68,34),(68,64)),((66,66),(10,66)),((8,64),(8,34))]: edge_line(a,z)
    for cx,cy,angle in [(66,34,-90),(66,64,0),(10,64,90),(10,34,180)]:
        def pt(a): return k.VECTOR2I(k.FromMM(cx+2*math.cos(math.radians(a))),k.FromMM(cy+2*math.sin(math.radians(a))))
        edge=k.PCB_SHAPE(); edge.SetShape(k.SHAPE_T_ARC); edge.SetArcGeometry(pt(angle),pt(angle+45),pt(angle+90)); edge.SetLayer(k.Edge_Cuts); edge.SetWidth(k.FromMM(.05)); b.Add(edge)
    # Full-height 2 mm copper barrier centered under isolator body. Not HV certification.
    z=k.ZONE(b); z.SetIsRuleArea(True); layers=k.LSET(); layers.AddLayer(k.F_Cu); layers.AddLayer(k.B_Cu); z.SetLayerSet(layers)
    z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(True); z.SetDoNotAllowZoneFills(True)
    poly=z.Outline(); poly.NewOutline()
    for x,y in [(74,0),(76,0),(76,100),(74,100)]: poly.Append(k.FromMM(x),k.FromMM(y))
    b.Add(z)
    for txt,x,y,size in [('VOLNLABS / AXIOM ROVER',38,83,1.4),('REV B - REVIEW ONLY',38,87,1),('PI 5 BELOW / 16.5 mm GAP',37,29,1),('ISOLATED UART',57,10,1),('POWER OFF TO SWAP',38,91,1),('SHRIKE R0.4',111.5,37,1.3),('USB END',111.5,14,1),('1',97,20,1),('1',126,20,1),('STOP NC',85,3,1),('HC-SR04',87,86,1),('SENSOR 5V',110,98,1),('6V FUSED',147,98,1),('L MOTOR',149,65,1),('R MOTOR',149,33,1),('ENC L',132,3,1),('ENC R',146,3,1),('IMU 3V3',140,18,1),('1A NOMINAL / CH',111,79,1)]:
        t=k.PCB_TEXT(b); t.SetText(txt); t.SetPosition(k.VECTOR2I(k.FromMM(x),k.FromMM(y))); t.SetTextSize(k.VECTOR2I(k.FromMM(size),k.FromMM(size))); t.SetTextThickness(k.FromMM(.15)); t.SetLayer(k.F_SilkS); b.Add(t)
    k.SaveBoard(str(ROOT/'carrier.kicad_pcb'),b)
    assert k.ExportSpecctraDSN(b,str(ROOT/'out/carrier.dsn'))
    (ROOT/'fp-lib-table').write_text('(fp_lib_table (lib (name "Rover") (type "KiCad") (uri "${KIPRJMOD}/Rover.pretty") (options "") (descr "Pinned KiCad 10 footprints")))\n')

def write_contract():
    with (ROOT/'out/assembly-bom.csv').open('w',newline='') as f:
        w=csv.writer(f,lineterminator="\n"); w.writerow(['Reference','Value / MPN','Footprint','Quantity'])
        for ref,val,fp,*rest in PARTS: w.writerow([ref,val,fp,1])
    (ROOT/'out/net-contract.json').write_text(json.dumps({p[0]:{str(i):n for i,n in enumerate(p[3],1)} for p in PARTS},indent=2)+'\n')

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--import-session',type=Path); parser.add_argument('--schematic-only',action='store_true'); parser.add_argument('--clean-dangling-vias',type=Path); args=parser.parse_args()
    if args.clean_dangling_vias:
        path=ROOT/'carrier.kicad_pcb'
        ids={i['uuid'] for v in json.loads(args.clean_dangling_vias.read_text())['violations'] if v['type']=='via_dangling' for i in v['items']}
        # KiCad 10.0.6 SWIG Remove(via) corrupts iteration; remove only UUID-matched
        # native top-level via records, then parse and refill with KiCad itself.
        source=path.read_text(); removed=set()
        def remove_via(match):
            block=match.group(); found=ids.intersection(re.findall(r'\(uuid "([^"]+)"\)',block))
            removed.update(found); return '' if found else block
        source=re.sub(r'(?ms)^\t\(via\b.*?^\t\)\n',remove_via,source)
        assert removed==ids, 'DRC cleanup report does not match this board'
        path.write_text(source)
        b=k.LoadBoard(str(path)); k.ZONE_FILLER(b).Fill(b.Zones()); k.SaveBoard(str(path),b)
    elif args.schematic_only:
        schematic()
    elif args.import_session:
        b=k.LoadBoard(str(ROOT/'carrier.kicad_pcb'))
        assert k.ImportSpecctraSES(b,str(args.import_session))
        values={p[0]:p[1] for p in PARTS}
        for fp in b.GetFootprints():
            if fp.GetReference() in values: fp.SetValue(values[fp.GetReference()])
        for track in b.GetTracks():
            if isinstance(track,k.PCB_VIA):
                if track.GetDrillValue()==k.FromMM(.6): track.SetWidth(k.FromMM(1.2))
            elif track.GetWidth()<k.FromMM(.2): track.SetWidth(k.FromMM(.2))
        # Complete the saved router session's local VM-to-decoupler connection.
        points=[(129.525,77),(129.525,78.1),(131.95,78.8),(131.95,80)]
        for a,z in zip(points,points[1:]):
            t=k.PCB_TRACK(b); t.SetNet(b.FindNet('/MOTOR_6V')); t.SetLayer(k.F_Cu); t.SetWidth(k.FromMM(.8)); t.SetLocked(True)
            t.SetStart(k.VECTOR2I(k.FromMM(a[0]),k.FromMM(a[1]))); t.SetEnd(k.VECTOR2I(k.FromMM(z[0]),k.FromMM(z[1]))); b.Add(t)
        # Ground copper also connects the exposed pad's thermal vias. Physical thermal
        # qualification remains required; an autorouter result is not a current rating.
        for name,x1,x2 in [('H_GND',.5,73.5),('BASE_GND',76.5,159.5)]:
            for layer in [k.F_Cu,k.B_Cu]:
                z=k.ZONE(b); z.SetLayer(layer); z.SetNet(b.FindNet('/'+name)); z.SetLocalClearance(k.FromMM(.2))
                z.SetPadConnection(k.ZONE_CONNECTION_FULL); z.SetMinThickness(k.FromMM(.2))
                poly=z.Outline(); poly.NewOutline()
                for x,y in [(x1,.5),(x2,.5),(x2,99.5),(x1,99.5)]: poly.Append(k.FromMM(x),k.FromMM(y))
                b.Add(z)
        k.ZONE_FILLER(b).Fill(b.Zones())
        k.SaveBoard(str(ROOT/'carrier.kicad_pcb'),b)
    else:
        (ROOT/'out').mkdir(exist_ok=True)
        (ROOT/'carrier.kicad_pro').write_text(json.dumps({'meta':{'filename':'carrier.kicad_pro','version':1},'board':{'design_settings':{'rules':{'min_clearance':.18,'min_track_width':.2,'min_via_diameter':.45,'min_through_hole_diameter':.2}}},'net_settings':{'classes':[{'name':'Default','clearance':.18,'track_width':.25,'via_diameter':.7,'via_drill':.3},{'name':'Motor','clearance':.2,'track_width':.8,'via_diameter':1.2,'via_drill':.6}],'netclass_patterns':[{'netclass':'Motor','pattern':'/MOTOR_*'},{'netclass':'Motor','pattern':'/SENSE_*'}],'meta':{'version':3}}},indent=2)+'\n')
        socket_footprints(); schematic(); board()
    write_contract()
