import rsa

# Use at least 2048 bit keys nowadays, see e.g. https://www.keylength.com/en/4/
publicKey, privateKey = rsa.newkeys(2048) 

# Export public key in PKCS#1 format, PEM encoded 
publicKeyPkcs1PEM = publicKey.save_pkcs1().decode('utf8') 
print(publicKeyPkcs1PEM)
# Export private key in PKCS#1 format, PEM encoded 
privateKeyPkcs1PEM = privateKey.save_pkcs1().decode('utf8') 
print(privateKeyPkcs1PEM)