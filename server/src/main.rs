use meeting_proto::meeting_room_service_server::{MeetingRoomService, MeetingRoomServiceServer};
use meeting_proto::{
    BookMeetingRequest, BookMeetingResponse, CancelMeetingRequest, CancelMeetingResponse, Meeting,
    QueryByIdRequest, QueryByIdResponse, QueryByOrganizerRequest, QueryByOrganizerResponse,
};
use std::collections::HashMap;
use std::sync::Mutex;
use tonic::{Request, Response, Status, transport::Server};

pub mod meeting_proto {
    tonic::include_proto!("proto.meeting");
}

/// 业务逻辑结构体
pub struct MyMeetingRoomService {
    /// 内存数据库：Key 是 ID，Value 是 Meeting
    meetings: Mutex<HashMap<i32, Meeting>>,
}

impl Default for MyMeetingRoomService {
    /// 创建一个新的 MyMeetingRoomService 实例，初始化一个空的会议数据库
    fn default() -> Self {
        Self {
            meetings: Mutex::new(HashMap::new()),
        }
    }
}

#[tonic::async_trait]
impl MeetingRoomService for MyMeetingRoomService {
    /// 预约会议室
    ///
    /// # Arguments
    ///
    /// * `request` - 包含会议详情的请求
    ///
    /// # Returns
    ///
    /// 包含预约结果的响应
    async fn book_meeting(
        &self,
        request: Request<BookMeetingRequest>,
    ) -> Result<Response<BookMeetingResponse>, Status> {
        println!("收到预约会议室请求");
        let req = request.into_inner();
        match req.meeting {
            Some(m) => {
                let mut db = self.meetings.lock().unwrap();
                let id = m.meeting_id;
                db.insert(id, m);

                Ok(Response::new(BookMeetingResponse {
                    success: true,
                    message: format!("ID {} 预约成功", id),
                }))
            }
            None => Ok(Response::new(BookMeetingResponse {
                success: false,
                message: "数据缺失".to_string(),
            })),
        }
    }

    /// 根据预约ID查询
    ///
    /// # Arguments
    ///
    /// * `request` - 包含预约ID的请求
    ///
    /// # Returns
    ///
    /// 包含查询结果的响应
    async fn query_by_id(
        &self,
        request: Request<QueryByIdRequest>,
    ) -> Result<Response<QueryByIdResponse>, Status> {
        println!("收到根据ID查询请求");
        let id = request.into_inner().meeting_id;
        let db = self.meetings.lock().unwrap();

        match db.get(&id) {
            Some(m) => Ok(Response::new(QueryByIdResponse {
                found: true,
                meeting: Some(m.clone()),
            })),
            None => Ok(Response::new(QueryByIdResponse {
                found: false,
                meeting: None,
            })),
        }
    }

    /// 根据组织者姓名查询
    ///
    /// # Arguments
    ///
    /// * `request` - 包含组织者姓名的请求
    ///
    /// # Returns
    ///
    /// 包含查询结果的响应
    async fn query_by_organizer(
        &self,
        request: Request<QueryByOrganizerRequest>,
    ) -> Result<Response<QueryByOrganizerResponse>, Status> {
        println!("收到根据组织者姓名查询请求");
        let name = request.into_inner().organizer_name;
        let db = self.meetings.lock().unwrap();
        let meetings: Vec<Meeting> = db
            .values()
            .filter(|m| m.organizer_name == name)
            .cloned()
            .collect();
        Ok(Response::new(QueryByOrganizerResponse {
            found: !meetings.is_empty(),
            meetings,
        }))
    }

    /// 取消指定会议预约
    ///
    /// # Arguments
    ///
    /// * `request` - 包含会议ID的请求
    ///
    /// # Returns
    ///
    /// 包含取消结果的响应
    async fn cancel_meeting(
        &self,
        request: Request<CancelMeetingRequest>,
    ) -> Result<Response<CancelMeetingResponse>, Status> {
        println!("收到取消会议预约请求");
        let id = request.into_inner().meeting_id;
        let mut db = self.meetings.lock().unwrap();
        match db.remove(&id) {
            Some(_) => Ok(Response::new(CancelMeetingResponse {
                success: true,
                message: format!("ID {} 取消成功", id),
            })),
            None => Ok(Response::new(CancelMeetingResponse {
                success: false,
                message: format!("ID {} 不存在", id),
            })),
        }
    }
}

/// 服务器入口函数，启动 gRPC 服务器并监听指定地址
///
/// # Returns
///
/// 一个包含错误信息的 Result，如果服务器启动失败则返回错误
#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let addr = "[::1]:50051".parse()?;
    let service = MyMeetingRoomService::default();

    println!("服务器已就绪: {}", addr);

    Server::builder()
        .add_service(MeetingRoomServiceServer::new(service))
        .serve(addr)
        .await?; // 只有这里必须保留 await，因为服务器要一直跑着

    Ok(())
}
