import sys,zlib,struct
def readpng(p):
    d=open(p,'rb').read(); pos=8; idat=b''
    while pos<len(d):
        n=struct.unpack('>I',d[pos:pos+4])[0]; t=d[pos+4:pos+8]; c=d[pos+8:pos+8+n]; pos+=12+n
        if t==b'IHDR': w,h=struct.unpack('>II',c[:8])
        if t==b'IDAT': idat+=c
    raw=zlib.decompress(idat); stride=w*4+1
    return w,h,[raw[y*stride+1:(y+1)*stride] for y in range(h)]
def writepng(p,rows,w,h):
    raw=b''.join(b'\0'[:1]+r for r in rows)
    ch=lambda t,c: struct.pack('>I',len(c))+t+c+struct.pack('>I',zlib.crc32(t+c)&0xffffffff)
    open(p,'wb').write(bytes([0x89])+b'PNG\r\n\x1a\n'+ch(b'IHDR',struct.pack('>IIBBBBB',w,h,8,6,0,0,0))+ch(b'IDAT',zlib.compress(raw))+ch(b'IEND',b''))
