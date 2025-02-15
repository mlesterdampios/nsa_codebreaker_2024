from concurrent import futures
import time
import grpc
import logging

import auth_pb2
import auth_pb2_grpc

_ONE_DAY_IN_SECONDS = 60 * 60 * 24

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Interceptor for handling logging on method not found or decoding errors
class LoggingInterceptor(grpc.ServerInterceptor):
    def intercept_service(self, continuation, handler_call_details):
        method = handler_call_details.method
        logging.info(f"Incoming request for method: {method}")
        
        try:
            # Call the actual service method
            response = continuation(handler_call_details)
            return response
        except grpc.RpcError as e:
            # Log error details
            if e.code() == grpc.StatusCode.UNIMPLEMENTED:
                logging.error(f"Method not found: {method}")
            elif e.code() == grpc.StatusCode.INVALID_ARGUMENT:
                logging.error(f"Request decoding error for method: {method}")
            else:
                logging.error(f"Error during request handling: {e}")
            raise e

class AuthService(auth_pb2_grpc.AuthServiceServicer):
    def log_metadata(self, context):
        # Log the incoming metadata (headers)
        metadata = context.invocation_metadata()
        logging.info("Received headers:")
        for key, value in metadata:
            logging.info(f"{key}: {value}")

    def Ping(self, request, context):
        # Log headers and request details
        self.log_metadata(context)
        logging.debug(f"Received Ping request: {request}")
        
        # Return the Ping response
        return auth_pb2.PingResponse(response=1)

    def Authenticate(self, request, context):
        # Log headers and request details
        self.log_metadata(context)
        logging.debug(f"Received Authenticate request: {request}")
        
        # Return the Authenticate response
        return auth_pb2.AuthResponse(success=True)

    def RegisterOTPSeed(self, request, context):
        # Log headers and request details
        self.log_metadata(context)
        logging.debug(f"Received RegisterOTPSeed request: {request}")
        
        # Return the RegisterOTPSeed response
        return auth_pb2.RegisterOTPSeedResponse(success=False)

    def VerifyOTP(self, request, context):
        # Log headers and request details
        self.log_metadata(context)
        logging.debug(f"Received VerifyOTP request: {request}")
        
        # Return the RegisterOTPSeed response
        return auth_pb2.VerifyOTPResponse(success=True,token="000000")

def serve():
    # Add the interceptor to the server
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        interceptors=[LoggingInterceptor()]
    )
    
    auth_pb2_grpc.add_AuthServiceServicer_to_server(AuthService(), server)
    server.add_insecure_port("[::]:50052")
    server.start()

    # Log the server start event
    logging.info("gRPC server started on port 50052")

    try:
        while True:
            time.sleep(_ONE_DAY_IN_SECONDS)
    except KeyboardInterrupt:
        # Log the server stop event
        logging.info("Stopping gRPC server...")
        server.stop(grace=0)
        logging.info("gRPC server stopped")

if __name__ == "__main__":
    serve()
