from math import sqrt
import socket

def sqroots(coeffs: str) -> str:
    a, b, c = map(int, coeffs.split())

    D = b**2 - 4 * a * c
    
    if D > 0:
        return ' '.join([ str((-b - sqrt(D))/(2*a)), str((-b + sqrt(D))/(2*a)) ])
    
    if D == 0:
        return str( -b/(2*a) )

    return ''


def sqrootnet(coeffs: str, s: socket.socket) -> str:
    s.sendall((coeffs + "\n").encode())
    return s.recv(128).decode().strip()


if __name__ == "__main__":
    import sys
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(("127.0.0.1", 1337))
        s.sendall(sys.argv[1].encode() + b'\n')
        print(s.recv(1024).rstrip().decode())