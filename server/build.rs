fn main() -> Result<(), Box<dyn std::error::Error>> {
    // 告诉 tonic-build 编译指定的 proto 文件
    tonic_prost_build::configure().compile_protos(
        &["../proto/meeting.proto"], // proto 文件的相对路径
        &["../proto"],               // proto 文件所在的搜索目录
    )?;
    Ok(())
}
