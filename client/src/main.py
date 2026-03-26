import sys
from datetime import datetime, timedelta
import questionary
from rich.console import Console
from rich.table import Table
from grpc_tools import protoc

class MeetingApp:
    """
    会议预约系统客户端：提供交互式命令行界面，支持预约、查询和取消会议
    """
    def __init__(self, host: str = 'localhost', port: int = 50051) -> None:
        """
        确保协议代码存在并进行初始化设置
        Args:
            host: 服务器地址，默认为 localhost
            port: 服务器端口，默认为 50051
        """
        self._ensure_protos()
        from service import MeetingClient
        self.client = MeetingClient(host=host, port=port)
        self.console = Console()

    def _ensure_protos(self) -> None:
        """
        确保 Protobuf 代码已生成：如果没有 meeting_pb2.py 或 meeting_pb2_grpc.py，则执行翻译
        """
        print("正在检查协议同步状态...")
        proto_path = "meeting.proto"
        
        # 执行翻译命令
        proto_args = [
            "grpc_tools.protoc",
            "-I../proto",
            "--python_out=./src",
            "--grpc_python_out=./src",
            proto_path,
        ]
        
        if protoc.main(proto_args) != 0:
            print("协议翻译失败，请检查 ../../proto 目录。")
            sys.exit(1)
        print("协议代码已就绪。")

    def close(self) -> None:
        """
        关闭客户端连接
        """
        self.client.close()

    def _parse_time(self, time_str: str) -> int:
        """
        解析时间字符串为时间戳
        Args:
            time_str: 格式为 "YYYY-MM-DD HH:MM" 的时间字符串
        Returns:
            成功解析返回对应的时间戳，失败返回0
        """
        try:
            dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
            return int(dt.timestamp())
        except ValueError:
            return 0

    def book_meeting(self):
        """
        交互式预约会议
        """
        self.console.print("\n[bold cyan]--- 预约新会议 ---[/bold cyan]")
        
        # 1. 文本输入
        meeting_id_str = questionary.text("请输入会议 ID (纯数字):").ask()
        if not meeting_id_str.isdigit():
            self.console.print("[red]ID 必须是纯数字！[/red]")
            return
        meeting_id = int(meeting_id_str)

        subject = questionary.text("请输入会议主题:").ask()
        organizer = questionary.text("请输入您的姓名:", default="admin").ask()

        # 2. 菜单选择 (支持上下方向键)
        room = questionary.select(
            "请选择会议室:",
            choices=["图灵会议室", "冯诺依曼会议室", "香农会议室", "Ada Lovelace 研讨室"]
        ).ask()

        # 3. 时间输入与基础校验
        start_str = questionary.text("请输入开始时间 (YYYY-MM-DD HH:MM):", default=datetime.now().strftime("%Y-%m-%d %H:%M")).ask()
        end_str = questionary.text("请输入结束时间 (YYYY-MM-DD HH:MM):", default=(datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")).ask()

        start_ts = self._parse_time(start_str)
        end_ts = self._parse_time(end_str)
        
        if start_ts == 0 or end_ts == 0:
            self.console.print("[red]时间格式错误，默认为0~1。[/red]")
            end_ts = 1
        if start_ts >= end_ts:
            self.console.print("[red]结束时间必须晚于开始时间！[/red]")
            return

        count_str = questionary.text("预计参与人数:", default="5").ask()
        count = int(count_str) if count_str.isdigit() else 5

        # 4. 最终确认
        if not questionary.confirm("确认提交以上预约信息吗？", default=True).ask():
            self.console.print("[yellow]已取消预约。[/yellow]")
            return

        # 发起 RPC 请求
        with self.console.status("[bold green]正在提交预约...[/bold green]"):
            success, msg = self.client.book_meeting(meeting_id, organizer, room, subject, start_ts, end_ts, count)

        if success:
            self.console.print(f"[bold green]✅ 预约成功：{msg}[/bold green]")
        else:
            self.console.print(f"[bold red]❌ 预约失败：{msg}[/bold red]")

    def query_by_id(self):
        """
        交互式根据 ID 查询会议详情
        """
        self.console.print("\n[bold cyan]--- 根据 ID 查询会议详情 ---[/bold cyan]")
        m_id_str = questionary.text("请输入要查询的会议 ID:").ask()
        if not m_id_str.isdigit():
            return
            
        with self.console.status(f"[bold cyan]正在查询...[/bold cyan]"):
            success, data = self.client.query_by_id(int(m_id_str))

        if success:
            table = Table(show_header=False, box=None)
            table.add_column("字段", style="cyan", justify="right")
            table.add_column("内容", style="magenta")
            table.add_row("主题:", data["subject"])
            table.add_row("组织者:", data["organizer"])
            table.add_row("会议室:", data["room"])
            table.add_row("时间:", f"{data['start']} 至 {data['end']}")
            table.add_row("人数:", str(data["count"]))
            self.console.print(table)
        else:
            self.console.print(f"[bold red]❌ 查询失败：{data}[/bold red]")

    def query_by_organizer(self):
        """
        交互式根据组织者查询会议
        """
        self.console.print("\n[bold cyan]--- 根据组织者查询会议 ---[/bold cyan]")
        organizer = questionary.text("请输入组织者姓名:", default="admin").ask()
        
        with self.console.status(f"[bold cyan]正在查询...[/bold cyan]"):
            success, data_list = self.client.query_by_organizer(organizer)

        if success:
            if not data_list:
                self.console.print("[yellow]暂无记录。[/yellow]")
                return
                
            table = Table(title=f"[{organizer}] 的会议列表")
            table.add_column("ID", justify="right", style="cyan")
            table.add_column("主题", style="magenta")
            table.add_column("会议室", style="green")
            table.add_column("时间区间", justify="center")
            for m in data_list:
                table.add_row(str(m["id"]), m["subject"], m["room"], f"{m['start']} ~ {m['end']}")
            self.console.print(table)
        else:
            self.console.print(f"[bold red]❌ 查询失败：{data_list}[/bold red]")

    def cancel_meeting(self):
        """
        交互式取消会议
        """
        self.console.print("\n[bold cyan]--- 取消会议 ---[/bold cyan]")
        m_id_str = questionary.text("请输入要取消的会议 ID:").ask()
        if not m_id_str.isdigit():
            return
            
        with self.console.status(f"[bold cyan]正在取消...[/bold cyan]"):
            success, msg = self.client.cancel_meeting(int(m_id_str))

        if success:
            self.console.print(f"[bold green]✅ 取消成功：{msg}[/bold green]")
        else:
            self.console.print(f"[bold red]❌ 取消失败：{msg}[/bold red]")

    def run(self):
        """
        主菜单循环
        """
        while True:
            action = questionary.select(
                "\n欢迎使用 RPC 会议室预约系统，请选择操作:",
                choices=[
                    "1. 预约新会议",
                    "2. 查询会议 (按 ID)",
                    "3. 查询会议 (按组织者)",
                    "4. 取消会议",
                    "5. 退出系统"
                ]
            ).ask()

            if action is None or action.startswith("5"):
                self.console.print("[dim]感谢使用，再见！[/dim]")
                break
            elif action.startswith("1"):
                self.book_meeting()
            elif action.startswith("2"):
                self.query_by_id()
            elif action.startswith("3"):
                self.query_by_organizer()
            elif action.startswith("4"):
                self.cancel_meeting()

if __name__ == "__main__":
    app = MeetingApp()
    try:
        app.run()
    except KeyboardInterrupt:
        print("\n程序被强制终止。")
    finally:
        app.close()
