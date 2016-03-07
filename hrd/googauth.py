import hashlib
import os
import base64
import time
import struct
import hmac



def generate_secret_key(length=16):
    """Generate random 16 character base 32 secret key.
    keys not padded so must be multiple of 4
    """
    if length < 8 or length > 128:
        raise TypeError('Secret key length is invalid.')

    # Generate sha1 hash of 8192 random bytes
    sha_hash = hashlib.sha512()
    sha_hash.update(os.urandom(8192))
    hexhash = sha_hash.hexdigest()

    # Rehash
    for i in xrange(6):
        sha_hash = hashlib.sha512()
        sha_hash.update(hexhash)
        hexhash = sha_hash.hexdigest()

    return base64.b32encode(hexhash)[:length]

def generate_code(secretkey, value=None):
    """Generate OTP code base on value. Value should be a counter value for
    counter based OTP or 30 second time block for time based OTP.

    Arguments:

    .. csv-table::
    :header: "argument", "type", "value"
    :widths: 7, 7, 40

    "*secretkey*", "string", "Base 32 secret key."
    "*value*", "number", "HOTP value. If ``None`` current 30 second time
    block will be used."

    Retruns:

    Six digit otp code.

    Usage::

    import googauth
    secret_key = googauth.generate_secret_key()
    print googauth.generate_code(secret_key)
    """
    value = value or int(time.time() / 30)

    # Convert value to bytes
    value = struct.pack('>q', value)

    # Decode base32 key to bytes
    secretkey = base64.b32decode(secretkey)

    # Generate HMAC-SHA1 from time based on secret key
    hash = hmac.new(secretkey, value, hashlib.sha1).digest()

    # Compute the truncated hash
    offset = ord(hash[-1]) & 0x0F
    truncated_hash = hash[offset:offset + 4]

    # Truncate to a smaller number of digits
    truncated_hash = struct.unpack('>L', truncated_hash)[0]
    truncated_hash &= 0x7FFFFFFF
    truncated_hash %= 1000000

    return '%06d' % truncated_hash


def verify_time_based(secretkey, code_attempt, window=3):
    """Verify a time based OTP against a secret key. By default the current
    time, 30 seconds back and forward are checked to compensate for time
    differences. Each code should first be check against previously used codes
    to prevent a code from being reused by an attacker in a MITM attack.

    Arguments:

    .. csv-table::
    :header: "argument", "type", "value"
    :widths: 7, 7, 40

    "*secretkey*", "string", "Base 32 secret key."
    "*code_attempt*", "string", "OTP code to be verfied."
    "*window*", "number", "Number of 30 second blocks to check for valid
    codes. This number is divided in half to check previous times and
    future times."

    Retruns:

    Time block that matched given code otherwise ``None`` if no match is
    found. This is the valid time divived by 30 not the actual time.

    Usage::

    import googauth
    secret_key = googauth.generate_secret_key()
    print googauth.verify_time_based(secret_key, '123456')
    """
    if isinstance(code_attempt, str) != True:
        raise TypeError('Code must be a string.')

    # Get current 30 second time block
    epoch = int(time.time() / 30)

    # Check valid codes for match
    for offset in xrange(window / 2 * -1, window - (window / 2)):
        valid_code = generate_code(secretkey, epoch + offset)

        if code_attempt == valid_code:
            return epoch + offset

    return None
