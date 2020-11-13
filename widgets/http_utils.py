from flask import request


def get_real_ip():
    ip = request.headers.get("x-forwarded-for")
    if ip is None or len(ip) == 0 or "unknown" == ip:
        ip = request.headers.get("Proxy-Client-IP")
    if ip is None or len(ip) == 0 or "unknown" == ip:
        ip = request.headers.get("WL-Proxy-Client-IP")
    if ip is None or len(ip) == 0 or "unknown" == ip:
        ip = request.remote_addr
    return ip
