import asyncio
import re
from prometheus_client import start_http_server, Gauge

# Метрики
iops = Gauge('vdbench_iops', 'IOPS')
latency = Gauge('vdbench_latency_ms', 'Latency in ms')
throughput = Gauge('vdbench_throughput_bytes', 'Throughput in bytes/sec')

LINE_REGEX = re.compile(
    r'(\d+\.\d+)\s+(\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)'
)
# пример: time iops mb/s latency

async def parse_vdbench_stream(stream):
    while True:
        line = await stream.readline()
        if not line:
            break

        line = line.decode('cp1251').strip()

        match = LINE_REGEX.search(line)
        if match:
            iops_val = float(match.group(2))
            mbps = float(match.group(3))
            lat = float(match.group(4))

            iops.set(iops_val)
            latency.set(lat)
            throughput.set(mbps * 1024 * 1024)

async def run_vdbench(vdbench_path):
    proc = await asyncio.create_subprocess_exec(
        "cmd", "/c",
        vdbench_path,
        "-t",
        stdout=asyncio.subprocess.PIPE
    )

    await parse_vdbench_stream(proc.stdout)

#TODO дописать работу офлайн
async def run_offline(file_path):
    with open(file_path, "rb") as f:
        for line in f:
            decoded = decode_line(line)
            print(decoded)  # или парсинг

            await asyncio.sleep(0.01)  # имитация realtime

def decode_line(line):
    pass
