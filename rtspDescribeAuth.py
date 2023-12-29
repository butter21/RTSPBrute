import socket

# Input for IP and port
ip = input("IP: ")
port = input("Port 554(1) or 8554(2): ")

# Simple functionality to set the port
if port == "1":
    port = 554
elif port == "2":
    port = 8554
else:
    port = 554
print(f"Port set to {port}")

# Constructing the request
req = f"DESCRIBE rtsp://{ip}:{port} RTSP/1.0\r\nCSeq: 2\r\nAuthorization: Basic YWRtaW46MTIzNA==\r\n\r\n"

# Initialize socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Convert port to integer
intPort = int(port)

# Try to make the connection
try:
    s.connect((ip, intPort))
except socket.error as e:
    print(f"Error connecting: {e}")
    exit()

# Try to send the request
s.sendall(req.encode())
data = s.recv(1024)
print("\n\n\n")
# Returning output
print(data.decode())  # Decode the received bytes to a string for printing
