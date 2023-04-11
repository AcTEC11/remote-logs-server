import uuid
from datetime import datetime
import argparse
import socket
import urllib
from aiohttp import web, WSMsgType

parser=argparse.ArgumentParser()
parser.add_argument("--heroku_app_domain", help="Heroku application domain")
parser.add_argument("--http_port", help="port to run HTTP server")

args=parser.parse_args()

http_port = int(args.http_port or '3000')
app_domain=args.heroku_app_domain or f"{socket.getfqdn()}"

# Create a dictionary to store the messages for each UUID
message_history = {}

# Start the HTTP server and WebSocket server
def main():
    async def main_handler(request):
        # print(f"scheme: {request.scheme}")
        # print(f"headers: {request.headers}")
        # return await http_main_handler(request)

        if 'upgrade' in request.headers and \
                request.headers.get('upgrade').lower() == 'websocket':
            return await websocket_session(request)
        else:
            return web.Response(status=200, text=f"wss://{request.host}")
    
    async def websocket_session(request):
        session_id = request.match_info.get('uuid') or str(uuid.uuid4())

        response = web.WebSocketResponse()
        await response.prepare(request)
        
        session_url = f"https://{request.host}/session/{urllib.parse.quote(session_id)}"

        print(f"WebSocket session URL: {session_url}")

        if not session_id in message_history:
            message_history[session_id] = []
        else:
            message_history[session_id].append('*' * 64)

        session_messages = message_history[session_id]

        user_message = f"[{datetime.now()}] session openned"
        session_messages.append(user_message)

        await response.send_str(session_url)

        async for message in response:
            if message.type == WSMsgType.ERROR:
                print(f"WebSocket error: {response.exception()}")
            elif message.type == WSMsgType.TEXT:
                # print(f"{session_id}: {message.data}")

                user_message = f"[{datetime.now()}] {message.data}"

                # Store the message in the UUID's message history
                session_messages.append(user_message)
        
        user_message = f"[{datetime.now()}] session closed"
        session_messages.append(user_message)
            
        print(f"WebSocket session {session_id} closed")

        return response
    
    async def session_handler(request):
        if 'upgrade' in request.headers and \
                request.headers.get('upgrade').lower() == 'websocket':
            return await websocket_session(request)
        else:
            return await http_session_handler(request)
    
    async def http_session_handler(request):
        uuid_str = request.match_info.get('uuid')
        if not uuid_str:
            return web.Response(text='Invalid UUID')

        # Retrieve the message history for this UUID
        if uuid_str in message_history:
            messages = '\n'.join(message_history[uuid_str])
            return web.Response(text=messages)
        else:
            return web.Response(text='No messages found for UUID')
    
    # print(f"http://{app_domain}:{http_port}")
    # print(f"ws://{app_domain}:{websocket_port}")

    app = web.Application()
    app.add_routes([web.get('/', main_handler)])
    app.add_routes([web.get('/session/{uuid}', session_handler)])
    web.run_app(app, port=http_port)

main()
