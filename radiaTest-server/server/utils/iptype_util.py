import ipaddress as ipaddr

def ip_type(ip):
    try:
        ipaddr.IPv4Address(ip)
        return True
    except ipaddr.AddressValueError:
        return False
