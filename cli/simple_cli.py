#!/usr/bin/env python3
"""
간단한 SDN CLI 인터페이스
Docker 컨테이너 상태 및 로그를 통해 네트워크 상태 확인
"""

import click
import subprocess
import json

@click.group()
def cli():
    """Simple SDN Management CLI"""
    pass

@cli.command()
def status():
    """네트워크 상태 확인"""
    click.echo("=== SDN Network Status ===")
    
    try:
        # Docker 컨테이너 상태 확인
        result = subprocess.run(['docker', 'ps', '--format', 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            click.echo("Container Status:")
            click.echo(result.stdout)
        else:
            click.echo(f"Error checking container status: {result.stderr}")
            
    except Exception as e:
        click.echo(f"Error: {e}")

@cli.command()
def controller_logs():
    """컨트롤러 로그 확인"""
    click.echo("=== Controller Logs ===")
    
    try:
        # Primary Controller 로그
        click.echo("Primary Controller (last 10 lines):")
        result = subprocess.run(['docker', 'logs', '--tail', '10', 'sdn-controller1'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            click.echo(result.stdout)
        else:
            click.echo(f"Error: {result.stderr}")
            
        click.echo("\nSecondary Controller (last 10 lines):")
        result = subprocess.run(['docker', 'logs', '--tail', '10', 'sdn-controller2'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            click.echo(result.stdout)
        else:
            click.echo(f"Error: {result.stderr}")
            
    except Exception as e:
        click.echo(f"Error: {e}")

@cli.command()
def network_test():
    """네트워크 연결성 테스트"""
    click.echo("=== Network Connectivity Test ===")
    
    try:
        # Mininet 컨테이너에서 네트워크 테스트 실행
        click.echo("Testing basic connectivity...")
        result = subprocess.run(['docker', 'exec', 'sdn-mininet', 'ping', '-c', '3', 'localhost'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            click.echo("✓ Basic connectivity: OK")
            click.echo(result.stdout)
        else:
            click.echo("✗ Basic connectivity: FAILED")
            click.echo(result.stderr)
            
    except Exception as e:
        click.echo(f"Error: {e}")

@cli.command()
def topology():
    """네트워크 토폴로지 정보"""
    click.echo("=== Network Topology ===")
    
    topology_info = {
        "switches": 10,
        "hosts": 20,
        "controllers": 2,
        "links": {
            "host-switch": 20,
            "switch-switch": 9
        },
        "tree_structure": {
            "root": "s1",
            "level_1": ["s2", "s3"],
            "level_2": ["s4", "s5", "s6", "s7"],
            "level_3": ["s8", "s9", "s10"]
        }
    }
    
    click.echo(f"Total Switches: {topology_info['switches']}")
    click.echo(f"Total Hosts: {topology_info['hosts']}")
    click.echo(f"Controllers: {topology_info['controllers']} (Primary + Secondary)")
    click.echo(f"Host-Switch Links: {topology_info['links']['host-switch']}")
    click.echo(f"Switch-Switch Links: {topology_info['links']['switch-switch']}")
    click.echo("\nTree Structure:")
    click.echo(f"  Root: {topology_info['tree_structure']['root']}")
    click.echo(f"  Level 1: {', '.join(topology_info['tree_structure']['level_1'])}")
    click.echo(f"  Level 2: {', '.join(topology_info['tree_structure']['level_2'])}")
    click.echo(f"  Level 3: {', '.join(topology_info['tree_structure']['level_3'])}")

@cli.command()
def mininet_info():
    """Mininet 네트워크 정보"""
    click.echo("=== Mininet Network Info ===")
    
    try:
        # Mininet 로그에서 토폴로지 정보 추출
        result = subprocess.run(['docker', 'logs', 'sdn-mininet'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            
            # Switch 정보 추출
            switch_lines = [line for line in lines if 'Switch s' in line and ': 00000000000000' in line]
            if switch_lines:
                click.echo("Connected Switches:")
                for line in switch_lines:
                    click.echo(f"  {line.strip()}")
            
            # 호스트 정보
            host_lines = [line for line in lines if '*** Adding hosts:' in line]
            if host_lines:
                click.echo(f"\nHosts: {host_lines[0].split(':', 1)[1].strip()}")
                
            # 링크 정보
            link_lines = [line for line in lines if '*** Adding links:' in line]
            if link_lines:
                click.echo(f"\nLinks: {link_lines[0].split(':', 1)[1].strip()}")
                
        else:
            click.echo(f"Error: {result.stderr}")
            
    except Exception as e:
        click.echo(f"Error: {e}")

@cli.command()
def interactive():
    """대화형 CLI 모드"""
    click.echo("=== Simple SDN CLI ===")
    click.echo("Available commands: status, controller-logs, network-test, topology, mininet-info, exit")
    
    while True:
        try:
            command = click.prompt("Simple-SDN> ", type=str).strip()
            
            if command == 'exit':
                break
            elif command == 'status':
                status.callback()
            elif command == 'controller-logs':
                controller_logs.callback()
            elif command == 'network-test':
                network_test.callback()
            elif command == 'topology':
                topology.callback()
            elif command == 'mininet-info':
                mininet_info.callback()
            elif command == 'help':
                click.echo("Commands: status, controller-logs, network-test, topology, mininet-info, exit")
            else:
                click.echo(f"Unknown command: {command}. Type 'help' for available commands.")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            click.echo(f"Error: {e}")
    
    click.echo("Goodbye!")

if __name__ == '__main__':
    cli()