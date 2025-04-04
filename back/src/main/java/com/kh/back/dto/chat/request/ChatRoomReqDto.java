package com.kh.back.dto.chat.request;

import com.kh.back.constant.ChatRoomType;
import lombok.*;

@Getter
@Setter
@NoArgsConstructor
@ToString
@AllArgsConstructor
public class ChatRoomReqDto { //채팅방 생성 요청시 전달되는 데이터
    private String name;
    private ChatRoomType roomType = ChatRoomType.GROUP; // 기본값 설정
    private Integer personCnt; // 참여 가능 인원 필드 추가
}
