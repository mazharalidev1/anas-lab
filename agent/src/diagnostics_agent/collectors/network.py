import psutil


def collect_network() -> dict:
    n = psutil.net_io_counters()
    return {"bytes_sent": n.bytes_sent, "bytes_received": n.bytes_recv, "packets_sent": n.packets_sent, "packets_received": n.packets_recv}
