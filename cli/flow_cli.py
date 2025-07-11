#!/usr/bin/env python3

import click
import requests
import json
from tabulate import tabulate

class SDNController:
    def __init__(self, primary_url="http://controller1:8080", secondary_url="http://controller2:8080"):
        self.primary_url = primary_url
        self.secondary_url = secondary_url
        self.active_controller = primary_url

    def send_request(self, endpoint, method='GET', data=None):
        """컨트롤러에 REST API 요청 전송"""
        try:
            url = f"{self.active_controller}{endpoint}"
            
            if method == 'GET':
                response = requests.get(url, timeout=5)
            elif method == 'POST':
                response = requests.post(url, json=data, timeout=5)
            elif method == 'DELETE':
                response = requests.delete(url, timeout=5)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}: {response.text}"}
                
        except requests.exceptions.RequestException as e:
            # Primary 컨트롤러 실패 시 Secondary로 전환
            if self.active_controller == self.primary_url:
                click.echo(f"Primary controller failed: {e}")
                click.echo("Switching to secondary controller...")
                self.active_controller = self.secondary_url
                return self.send_request(endpoint, method, data)
            else:
                return {"error": f"Both controllers failed: {e}"}

@click.group()
@click.pass_context
def cli(ctx):
    """SDN Flow Management CLI"""
    ctx.ensure_object(dict)
    ctx.obj['controller'] = SDNController()

@cli.command()
@click.pass_context
def status(ctx):
    """네트워크 상태 확인"""
    controller = ctx.obj['controller']
    
    click.echo("=== SDN Network Status ===")
    
    # Primary 컨트롤러 상태
    click.echo(f"Active Controller: {controller.active_controller}")
    
    # 플로우 정보 조회
    flows = controller.send_request("/flows")
    if "error" in flows:
        click.echo(f"Error: {flows['error']}")
    else:
        click.echo(f"Connected Switches: {len(flows.get('flows', {}))}")
        for dpid, mac_table in flows.get('flows', {}).items():
            click.echo(f"  Switch {dpid}: {len(mac_table)} MAC entries")

@cli.command()
@click.pass_context
def list_flows(ctx):
    """플로우 테이블 조회"""
    controller = ctx.obj['controller']
    
    flows = controller.send_request("/flows")
    if "error" in flows:
        click.echo(f"Error: {flows['error']}")
        return
    
    click.echo("=== Flow Tables ===")
    for dpid, mac_table in flows.get('flows', {}).items():
        click.echo(f"\nSwitch {dpid}:")
        if mac_table:
            table_data = [[mac, port] for mac, port in mac_table.items()]
            click.echo(tabulate(table_data, headers=['MAC Address', 'Port'], tablefmt='grid'))
        else:
            click.echo("  No flows installed")

@cli.command()
@click.option('--dpid', required=True, type=int, help='Switch DPID')
@click.option('--priority', default=1, type=int, help='Flow priority')
@click.option('--in-port', type=int, help='Input port')
@click.option('--eth-src', help='Source MAC address')
@click.option('--eth-dst', help='Destination MAC address')
@click.option('--output', required=True, type=int, help='Output port')
@click.pass_context
def add_flow(ctx, dpid, priority, in_port, eth_src, eth_dst, output):
    """플로우 규칙 추가"""
    controller = ctx.obj['controller']
    
    flow_data = {
        'dpid': dpid,
        'priority': priority,
        'output': output
    }
    
    if in_port is not None:
        flow_data['in_port'] = in_port
    if eth_src:
        flow_data['eth_src'] = eth_src
    if eth_dst:
        flow_data['eth_dst'] = eth_dst
    
    result = controller.send_request("/flows", method='POST', data=flow_data)
    
    if "error" in result:
        click.echo(f"Error: {result['error']}")
    else:
        click.echo(f"Flow added successfully: {result.get('message', 'OK')}")

@cli.command()
@click.option('--controller', type=click.Choice(['primary', 'secondary']), default='primary')
@click.pass_context
def switch_controller(ctx, controller):
    """활성 컨트롤러 변경"""
    sdn_controller = ctx.obj['controller']
    
    if controller == 'primary':
        sdn_controller.active_controller = sdn_controller.primary_url
    else:
        sdn_controller.active_controller = sdn_controller.secondary_url
    
    click.echo(f"Switched to {controller} controller: {sdn_controller.active_controller}")

@cli.command()
@click.pass_context
def monitor(ctx):
    """네트워크 모니터링 (실시간)"""
    import time
    
    controller = ctx.obj['controller']
    
    click.echo("=== Real-time Network Monitoring ===")
    click.echo("Press Ctrl+C to stop")
    
    try:
        while True:
            click.clear()
            click.echo("=== SDN Network Monitor ===")
            click.echo(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            click.echo(f"Active Controller: {controller.active_controller}")
            
            # 플로우 정보 조회
            flows = controller.send_request("/flows")
            if "error" not in flows:
                click.echo(f"Connected Switches: {len(flows.get('flows', {}))}")
                for dpid, mac_table in flows.get('flows', {}).items():
                    click.echo(f"  Switch {dpid}: {len(mac_table)} active flows")
            
            time.sleep(2)
            
    except KeyboardInterrupt:
        click.echo("\nMonitoring stopped.")

@cli.command()
@click.pass_context
def interactive(ctx):
    """대화형 CLI 모드"""
    controller = ctx.obj['controller']
    
    click.echo("=== SDN Interactive CLI ===")
    click.echo("Available commands: status, list-flows, add-flow, switch-controller, monitor, exit")
    
    while True:
        try:
            command = click.prompt("SDN> ", type=str).strip()
            
            if command == 'exit':
                break
            elif command == 'status':
                ctx.invoke(status)
            elif command == 'list-flows':
                ctx.invoke(list_flows)
            elif command == 'monitor':
                ctx.invoke(monitor)
            elif command.startswith('add-flow'):
                click.echo("Use: add-flow --dpid <dpid> --output <port> [--in-port <port>] [--eth-src <mac>] [--eth-dst <mac>]")
            elif command == 'help':
                click.echo("Commands: status, list-flows, add-flow, switch-controller, monitor, exit")
            else:
                click.echo(f"Unknown command: {command}. Type 'help' for available commands.")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            click.echo(f"Error: {e}")
    
    click.echo("Goodbye!")

if __name__ == '__main__':
    cli()