import asyncio

async def echo(reader, writer):
    host, port = writer.get_extra_info('peername')
    while data := await reader.readline():
        cmd = data.split()
        match cmd:
            case [b'print', *tail]:
                writer.write(b' '.join(tail) + b'\n')
            case [b'info', b'host']:
                writer.write(host.encode() + b'\n')
            case [b'info', b'ort']:
                writer.write(str(port).encode() + b'\n')
            case _:
                writer.write(b'Uncnown command\n')
        print(data)
    writer.close()
    await writer.wait_closed()

async def main():
    server = await asyncio.start_server(echo, '0.0.0.0', 1337)
    async with server:
        await server.serve_forever()


asyncio.run(main())
