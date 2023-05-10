import rsa

with open("rsafiles/private.pem","r") as file:
    data = file.read()
    privateKeyReloaded = rsa.PrivateKey.load_pkcs1(data.encode('utf8')) 

with open("rsafiles/public.pem","r") as file:
    data = file.read()
    publicKeyReloaded = rsa.PublicKey.load_pkcs1(data.encode('utf8')) 