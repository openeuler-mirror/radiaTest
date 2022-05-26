import ipaddress as ipaddr

def ip_type(ip):
    try:
        ipaddr.IPv4Address(ip)
    except ipaddr.AddressValueError: "IP format error,Please check."
