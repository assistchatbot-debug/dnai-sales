import signal, sys
def register_shutdown(dp, bot):
    def handler(signum, frame):
        asyncio.create_task(shutdown(dp, bot))
        sys.exit(0)
    signal.signal(signal.SIGTERM, handler)
