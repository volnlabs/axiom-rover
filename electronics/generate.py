#!/usr/bin/env python3
"""Generate review-revision carrier source with KiCad's bundled pcbnew Python.
Re-running replaces CAD edits: use generated KiCad files directly for manual revision.
"""
import argparse, csv, json, os, uuid, shutil
from pathlib import Path
import pcbnew as k

ROOT = Path(__file__).resolve().parent
UID = lambda s: str(uuid.uuid5(uuid.NAMESPACE_URL, 'volnlabs/axiom-rover/carrier/'+s))
SHEET = UID('sheet')
def xh(n): return f'Connector_JST:JST_XH_B{n}B-XH-A_1x{n:02d}_P2.50mm_Vertical'
R = 'Resistor_SMD:R_0805_2012Metric'
C = 'Capacitor_SMD:C_0805_2012Metric'
# ref, value, footprint, pin-number-ordered nets, PCB x/y/angle, schematic x/y
PARTS = [
('J1','HOST_UART_3V3',xh(4),['HOST_3V3','H_GND','H_TX','H_RX'],(9,20,0),(55,50)),
('U1','ISO7721DR','Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',['HOST_3V3','H_RX','H_TX','H_GND','BASE_GND','RP_UART_RX','RP_UART_TX','BASE_3V3'],(30,25,0),(145,50)),
('C1','100nF 16V X7R',C,['HOST_3V3','H_GND'],(24,25,-90),(50,88)),
('C2','100nF 16V X7R',C,['BASE_3V3','BASE_GND'],(36,25,-90),(145,88)),
('J2','SHRIKE_HARNESS','Connector_IDC:IDC-Header_2x08_P2.54mm_Vertical',['BASE_3V3','BASE_GND','ESTOP_N','L_IN1','L_IN2','R_IN3','R_IN4','US_TRIG','US_ECHO_3V','RP_UART_TX','RP_UART_RX','ESTOP_N','FPGA_PWM_L','FPGA_PWM_R',None,None],(60,20,0),(65,168)),
('J3','HC_SR04',xh(4),['BASE_5V','BASE_GND','SENSOR_TRIG','US_ECHO_5V'],(99,58,0),(335,50)),
('R1','1k 1%',R,['US_TRIG','SENSOR_TRIG'],(84,48,0),(245,90)),
('R2','2.2k 1%',R,['US_ECHO_5V','ECHO_DIV'],(96,48,0),(335,90)),
('R3','3.3k 1%',R,['ECHO_DIV','BASE_GND'],(91,43,90),(335,120)),
('U2','SN74LVC1G17DBVR','Package_TO_SOT_SMD:SOT-23-5',[None,'ECHO_DIV','BASE_GND','US_ECHO_3V','BASE_3V3'],(85,39,0),(245,50)),
('C3','100nF 16V X7R',C,['BASE_3V3','BASE_GND'],(80,39,90),(245,120)),
('J4','L298N_LOGIC',xh(7),['BASE_GND','L_IN1','L_IN2','R_IN3','R_IN4','FPGA_PWM_L','FPGA_PWM_R'],(92,17,0),(165,160)),
('R4','10k 1%',R,['ESTOP_N','BASE_GND'],(69,55,0),(150,208)),
('R5','10k 1%',R,['FPGA_PWM_L','BASE_GND'],(98,27,90),(245,205)),
('R6','10k 1%',R,['FPGA_PWM_R','BASE_GND'],(106,27,90),(335,205)),
('J5','ESTOP_NC_LOOP',xh(2),['BASE_3V3','ESTOP_N'],(65,67,0),(245,160)),
('J6','SENSOR_5V_IN',xh(2),['BASE_5V','BASE_GND'],(96,69,0),(335,160)),
]

def pin_info(ref,n,net):
    if ref=='U1':
        names=['VCC1','OUTA','INB','GND1','GND2','OUTB','INA','VCC2']
        types=['power_in','output','input','power_in','power_in','output','input','power_in']
        side=-1 if n<=4 else 1
        return names[n-1],types[n-1],side,((2.5-n) if n<=4 else (n-6.5))*5.08
    if ref=='U2':
        names=['NC','A','GND','Y','VCC']; types=['no_connect','input','power_in','output','power_in']
        return names[n-1],types[n-1],-1,(3-n)*5.08
    return str(n),'passive',-1,0 # assigned spacing below

def schematic():
    libs=[]; items=[]
    for ref,val,fp,nets,place,(x,y) in PARTS:
        x=round(x/1.27)*1.27; y=round(y/1.27)*1.27
        name=ref; half=max(7.62,(len(nets)+1)*2.54) if not ref.startswith('U') else 15.24
        if ref[0] in "RC": half=3.81
        pins=[]; pdata=[]
        for n,net in enumerate(nets,1):
            label,typ,side,dy=pin_info(ref,n,net)
            if not ref.startswith('U'): dy=((len(nets)+1)/2-n)*5.08
            if ref[0] in "RC": side=-1 if n==1 else 1; dy=0
            px=side*(7.62 if ref[0] in 'RC' else 15.24); ang=0 if side<0 else 180
            length=(6.35 if ref[0]=='C' else 5.08)
            pins.append(f'(pin {typ} line (at {px} {dy} {ang}) (length {length}) (name "{label}" (effects (font (size 1.0 1.0)))) (number "{n}" (effects (font (size 1.0 1.0)))))')
            pdata.append((n,net,x+px,y-dy,side))
        graphic=f'(rectangle (start -10.16 {half}) (end 10.16 {-half}) (stroke (width 0.254) (type default)) (fill (type background)))'
        if ref[0]=='R': graphic='(rectangle (start -2.54 1.27) (end 2.54 -1.27) (stroke (width 0.254) (type default)) (fill (type none)))'
        if ref[0]=='C': graphic=''.join(f'(polyline (pts (xy {a} -2.54) (xy {a} 2.54)) (stroke (width 0.254) (type default)) (fill (type none)))' for a in (-1.27,1.27))
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
    for i,net in enumerate(['HOST_3V3','H_GND','BASE_3V3','BASE_GND','BASE_5V']):
        x=round((40+i*65)/1.27)*1.27; y=round(240/1.27)*1.27; ref=f'#FLG0{i+1}'
        items.append(f'''(symbol (lib_id "Rover:PWR_FLAG") (at {x} {y} 0) (unit 1) (in_bom no) (on_board no) (uuid "{UID(ref)}")
          (property "Reference" "{ref}" (at {x} {y-3} 0) (effects (font (size 1 1)) hide))
          (property "Value" "OFFBOARD RAIL" (at {x} {y-5} 0) (effects (font (size 1 1))))
          (pin "1" (uuid "{UID(ref+'pin')}"))
          (instances (project "carrier" (path "/{SHEET}" (reference "{ref}") (unit 1)))))
          (label "{net}" (at {x} {y} 0) (effects (font (size 1 1)) (justify left bottom)) (uuid "{UID(ref+'label')}"))''')
    for i,(txt,x,y) in enumerate([
        ('HOST / BASE ISOLATION — no copper or ground tie across U1',105,18),
        ('HC-SR04: protected echo input; 5 V stays on base',285,18),
        ('FPGA outputs only: ENA / ENB jumpers removed; local driver pull-downs required',225,222),
        ('REVIEW REV A — motors, fuse, relay, dual-NC stop and all high-current wiring OFF BOARD',165,262),
        ('J5 is logic NC loop only. J6 is sensor supply only. Power down before swapping trays.',165,268)]):
        items.append(f'(text "{txt}" (at {x} {y} 0) (effects (font (size 1.27 1.27))) (uuid "{UID("note"+str(i))}"))')
    (ROOT/'carrier.kicad_sch').write_text(f'(kicad_sch (version 20250114) (generator "rover_generator") (uuid "{SHEET}") (paper "A3") (title_block (title "Axiom Rover — isolated low-current carrier") (date "2026-09-09") (rev "A REVIEW")) (lib_symbols {"".join(libs)}) {"".join(items)} (sheet_instances (path "/" (page "1"))))\n')
    (ROOT/'Rover.kicad_sym').write_text('(kicad_symbol_lib (version 20241209) (generator "rover_generator") '+''.join(s.replace('"Rover:','"',1) for s in libs)+')\n')
    (ROOT/'sym-lib-table').write_text('(sym_lib_table (lib (name "Rover") (type "KiCad") (uri "${KIPRJMOD}/Rover.kicad_sym") (options "") (descr "Carrier review symbols")))\n')

    # Keep schematic footprint identifiers consistent with the embedded board library.
    for file in ['carrier.kicad_sch','Rover.kicad_sym']:
        p=ROOT/file; s=p.read_text()
        for part in PARTS: s=s.replace(part[2],'Rover:'+part[2].split(':')[1])
        p.write_text(s)

def board():
    b=k.BOARD(); b.SetCopperLayerCount(2)
    settings=b.GetDesignSettings(); nc=settings.m_NetSettings.GetDefaultNetclass(); nc.SetClearance(k.FromMM(.25)); nc.SetTrackWidth(k.FromMM(.3)); nc.SetViaDiameter(k.FromMM(.7)); nc.SetViaDrill(k.FromMM(.3)); settings.SetBoardThickness(k.FromMM(1.6))
    settings.m_MinClearance=k.FromMM(.25); settings.m_TrackMinWidth=k.FromMM(.25)
    settings.m_ViasMinSize=k.FromMM(.7); settings.m_MinThroughDrill=k.FromMM(.3)
    nets={}
    for name in sorted({n for p in PARTS for n in p[3] if n}):
        net=k.NETINFO_ITEM(b,"/"+name); b.Add(net); nets[name]=net
    libroot=Path(os.environ.get('KICAD10_FOOTPRINT_DIR',str(Path(os.environ.get('APPDIR','/usr'))/'share/kicad/footprints')))
    local=ROOT/'Rover.pretty'; local.mkdir(exist_ok=True)
    def footprint(libid,ref,val,x,y,angle):
        lib,name=libid.split(':'); fp=k.FootprintLoad(str(libroot/(lib+'.pretty')),name)
        if fp is None: raise RuntimeError(f'Missing footprint: {libid}')
        shutil.copyfile(libroot/(lib+".pretty")/(name+".kicad_mod"), local/(name+".kicad_mod"))
        fp.SetFPID(k.LIB_ID('Rover',name)); fp.SetReference(ref); fp.SetValue(val)
        fp.SetPosition(k.VECTOR2I(k.FromMM(x),k.FromMM(y))); fp.SetOrientationDegrees(angle)
        fp.Value().SetVisible(False); fp.Reference().SetTextSize(k.VECTOR2I(k.FromMM(1),k.FromMM(1))); fp.Reference().SetTextThickness(k.FromMM(.15))
        fp.Reference().SetPosition(k.VECTOR2I(k.FromMM(x),k.FromMM(y-(7 if ref=="J2" else 4))))
        b.Add(fp); return fp
    for ref,val,libid,pinnets,(x,y,angle),sch in PARTS:
        fp=footprint(libid,ref,val,x,y,angle)
        fp.SetPath(k.KIID_PATH('/'+SHEET+'/'+UID(ref)))
        for pad in fp.Pads():
            n=int(pad.GetNumber()); net=pinnets[n-1]
            if net: pad.SetNet(nets[net])
            else:
                ncname=f'unconnected-({ref}-'+('NC-' if ref=='U2' else '')+f'Pad{n})'
                ncnet=k.NETINFO_ITEM(b,ncname); b.Add(ncnet); pad.SetNet(ncnet)
    for i,(x,y) in enumerate([(5,5),(115,5),(115,75),(5,75)],1):
        fp=footprint('MountingHole:MountingHole_3.2mm_M3',f'H{i}','M3 NPTH',x,y,0)
        fp.SetAttributes(k.FP_BOARD_ONLY|k.FP_EXCLUDE_FROM_BOM|k.FP_EXCLUDE_FROM_POS_FILES)
        fp.Reference().SetVisible(False)
    for a,z in [((0,0),(120,0)),((120,0),(120,80)),((120,80),(0,80)),((0,80),(0,0))]:
        edge=k.PCB_SHAPE(); edge.SetShape(k.SHAPE_T_SEGMENT); edge.SetStart(k.VECTOR2I(k.FromMM(a[0]),k.FromMM(a[1]))); edge.SetEnd(k.VECTOR2I(k.FromMM(z[0]),k.FromMM(z[1]))); edge.SetLayer(k.Edge_Cuts); edge.SetWidth(k.FromMM(.05)); b.Add(edge)
    # Full-height 2 mm copper barrier centered under isolator body. Not HV certification.
    z=k.ZONE(b); z.SetIsRuleArea(True); layers=k.LSET(); layers.AddLayer(k.F_Cu); layers.AddLayer(k.B_Cu); z.SetLayerSet(layers)
    z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(True); z.SetDoNotAllowZoneFills(True)
    poly=z.Outline(); poly.NewOutline()
    for x,y in [(29,0),(31,0),(31,80),(29,80)]: poly.Append(k.FromMM(x),k.FromMM(y))
    b.Add(z)
    for txt,x,y,size in [('VOLNLABS / AXIOM ROVER',75,7,1.4),('REV A - REVIEW ONLY',75,10,1),('HOST',13,10,1.2),('ISOLATED',14,47,1),('POWER OFF',14,52,1),('TO SWAP',14,55,1),('NO MOTOR CURRENT ON PCB',78,76,1),('STOP NC',67,59.5,1),('5V SENSOR',86,72,1),('HC-SR04',103,51,1),('L298 LOGIC',98,9,1)]:
        t=k.PCB_TEXT(b); t.SetText(txt); t.SetPosition(k.VECTOR2I(k.FromMM(x),k.FromMM(y))); t.SetTextSize(k.VECTOR2I(k.FromMM(size),k.FromMM(size))); t.SetTextThickness(k.FromMM(.15)); t.SetLayer(k.F_SilkS); b.Add(t)
    k.SaveBoard(str(ROOT/'carrier.kicad_pcb'),b)
    assert k.ExportSpecctraDSN(b,str(ROOT/'out/carrier.dsn'))
    (ROOT/'fp-lib-table').write_text('(fp_lib_table (lib (name "Rover") (type "KiCad") (uri "${KIPRJMOD}/Rover.pretty") (options "") (descr "Pinned KiCad 10 footprints")))\n')
    with (ROOT/'out/assembly-bom.csv').open('w',newline='') as f:
        w=csv.writer(f); w.writerow(['Reference','Value / MPN','Footprint','Quantity'])
        for ref,val,fp,*rest in PARTS: w.writerow([ref,val,fp,1])
    (ROOT/'out/net-contract.json').write_text(json.dumps({p[0]:{str(i):n for i,n in enumerate(p[3],1)} for p in PARTS},indent=2)+'\n')

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--import-session',type=Path); parser.add_argument('--schematic-only',action='store_true'); args=parser.parse_args()
    if args.schematic_only:
        schematic()
    elif args.import_session:
        b=k.LoadBoard(str(ROOT/'carrier.kicad_pcb'))
        assert k.ImportSpecctraSES(b,str(args.import_session))
        for track in b.GetTracks():
            if not isinstance(track,k.PCB_VIA) and track.GetWidth()<k.FromMM(.25): track.SetWidth(k.FromMM(.25))
        k.SaveBoard(str(ROOT/'carrier.kicad_pcb'),b)
    else:
        (ROOT/'out').mkdir(exist_ok=True)
        (ROOT/'carrier.kicad_pro').write_text(json.dumps({'meta':{'filename':'carrier.kicad_pro','version':1},'net_settings':{'classes':[{'name':'Default','clearance':.25,'track_width':.3,'via_diameter':.7,'via_drill':.3}],'meta':{'version':3}}},indent=2)+'\n')
        schematic(); board()
