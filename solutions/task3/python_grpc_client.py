import argparse

import grpc

import seed_generation_pb2
import seed_generation_pb2_grpc

def run(host):
    channel = grpc.insecure_channel(host)
    stub = seed_generation_pb2_grpc.SeedGenerationServiceStub(channel)

    response = stub.GetSeed(seed_generation_pb2.GetSeedRequest(username="jasper_05376",password="test"))
    print("SeedGenerationService client received: Seed=" + str(response.seed) + ", Count=" + str(response.count))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--host", default="localhost:50051", help="The server host.")
    args = parser.parse_args()
    run(args.host)