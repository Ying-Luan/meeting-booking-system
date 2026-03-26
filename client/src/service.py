import grpc
from datetime import datetime
import meeting_pb2
import meeting_pb2_grpc
from typing import Tuple

class MeetingClient:
    """
    gRPC 客户端：封装与服务器的通信细节，提供简洁的接口供 UI 调用
    """
    def __init__(self, host: str = 'localhost', port: int = 50051):
        """
        初始化 gRPC 客户端连接
        Args:
            host: 服务器地址，默认为 localhost
            port: 服务器端口，默认为 50051
        """
        self.target = f"{host}:{port}"
        self.channel = grpc.insecure_channel(self.target)
        self.stub = meeting_pb2_grpc.MeetingRoomServiceStub(self.channel)

    def _handle_error(self, e):
        """
        统一错误处理逻辑
        Args:
            e: 捕获的异常对象
        """
        if isinstance(e, grpc.RpcError):
            return f"RPC错误 ({e.code()}): {e.details()}"
        return f"未知错误: {str(e)}"

    def book_meeting(self, meeting_id: int, organizer_name: str, room_name: str="", subject: str="", start_ts: int=0, end_ts: int=0, participant_count: int=0) -> Tuple[bool, str]:
        """
        封装预约接口：隐藏 pb2.Meeting 构造细节
        Args:
            meeting_id: 会议ID
            organizer_name: 组织者姓名
            room_name: 会议室名称
            subject: 会议主题
            start_ts: 开始时间戳
            end_ts: 结束时间戳
            participant_count: 参与人数
        Returns:
            成功返回 (True, 成功信息)，失败返回 (False, 错误信息)
        """
        try:
            # 构造协议对象
            meeting = meeting_pb2.Meeting(
                meeting_id=meeting_id,
                organizer_name=organizer_name,
                room_name=room_name,
                subject=subject,
                start_time=int(start_ts),
                end_time=int(end_ts),
                participant_count=participant_count
            )
            req = meeting_pb2.BookMeetingRequest(meeting=meeting)
            
            # 调用并返回
            resp = self.stub.BookMeeting(req)
            return resp.success, resp.message
        except Exception as e:
            return False, self._handle_error(e)

    def query_by_id(self, meeting_id: int) -> Tuple[bool, dict]:
        """
        根据ID查询：将 Protobuf 对象转为 Python 字典以便 UI 展示
        Args:
            meeting_id: 会议ID
        Returns:
            成功返回 (True, 会议信息)，失败返回 (False, 错误信息字典)
        """
        try:
            req = meeting_pb2.QueryByIDRequest(meeting_id=meeting_id)
            resp = self.stub.QueryByID(req)
            if resp.found:
                return True, self._meeting_to_dict(resp.meeting)
            return False, {}
        except Exception as e:
            return False, {"error": self._handle_error(e)}

    def query_by_organizer(self, organizer_name: str) -> Tuple[bool, list]:
        """
        返回列表：自动处理 repeated 字段
        Args:
            organizer_name: 组织者姓名
        Returns:
            成功返回 (True, 会议信息列表)，失败返回 (False, 错误信息列表)
        """
        try:
            req = meeting_pb2.QueryByOrganizerRequest(organizer_name=organizer_name)
            resp = self.stub.QueryByOrganizer(req)
            if resp.found:
                return True, [self._meeting_to_dict(m) for m in resp.meetings]
            return False, []
        except Exception as e:
            return False, [self._handle_error(e)]

    def cancel_meeting(self, meeting_id: int) -> Tuple[bool, str]:
        """
        取消会议：简单封装取消接口
        Args:
            meeting_id: 会议ID
        Returns:
            成功返回 (True, 成功信息)，失败返回 (False, 错误信息)
        """
        try:
            req = meeting_pb2.CancelMeetingRequest(meeting_id=meeting_id)
            resp = self.stub.CancelMeeting(req)
            return resp.success, resp.message
        except Exception as e:
            return False, self._handle_error(e)

    def _meeting_to_dict(self, m) -> dict:
        """
        内部工具：转换数据格式，避免前端直接依赖 pb2 结构
        Args:
            m: Protobuf Meeting 对象
        Returns:
            转换后的 Python 字典
        """
        return {
            "id": m.meeting_id,
            "organizer": m.organizer_name,
            "room": m.room_name,
            "subject": m.subject,
            "start": datetime.fromtimestamp(m.start_time).strftime('%Y-%m-%d %H:%M'),
            "end": datetime.fromtimestamp(m.end_time).strftime('%Y-%m-%d %H:%M'),
            "count": m.participant_count
        }

    def close(self):
        """
        关闭 gRPC 连接
        """
        self.channel.close()
