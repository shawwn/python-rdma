import codecs

def encode_hex(s):
  return codecs.encode(s, "hex")

def tobytes(s):
  if isinstance(s, str):
    return s.encode('utf-8')
  return s