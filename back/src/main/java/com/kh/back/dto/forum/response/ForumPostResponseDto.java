package com.kh.back.dto.forum.response;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.kh.back.dto.python.SearchResDto;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.time.OffsetDateTime;
import java.util.List;

/**
 * 게시글 응답 DTO
 * KR: 클라이언트에 게시글 정보와 콘텐츠(HTML, JSON)를 전달하는 DTO.
 */
@Data
@Builder
@AllArgsConstructor
@NoArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
public class ForumPostResponseDto extends SearchResDto {
    @JsonProperty("id")
    private String id; // 게시글 ID
    private String title; // 게시글 제목
    private String content; // 게시글 내용 (HTML)
    private String authorName; // 작성자 이름
    private Long memberId; // 작성자 ID
    private Boolean sticky; // 상단 고정 여부
    private Integer viewsCount; // 조회수
    private Integer likesCount; // 좋아요 수
    private Boolean hidden; // 숨김 여부
    private String removedBy; // 삭제자 정보
    private String editedByTitle; // 제목 수정자 정보
    private String editedByContent; // 내용 수정자 정보
    private Boolean locked; // 수정 불가능 여부
    private OffsetDateTime createdAt; // 생성시간
    private OffsetDateTime updatedAt; // 수정시간
    private ForumPostCommentResponseDto latestComment; // 최신 댓글 객체
    private Boolean editedTitleByAdmin; // 제목이 관리자에 의해 수정되었는지 여부
    private Boolean editedContentByAdmin; // 내용이 관리자에 의해 수정되었는지 여부
    private List<String> fileUrls; // 첨부 파일 URL 목록
    private Integer reportCount; // 신고 횟수
    private Boolean hasReported; // 신고 여부
    private String contentJSON; // 게시글 콘텐츠의 JSON 표현 (Tiptap JSON)
    private String category; // 게시글 카테고리 (ES에서 categoryId가 복사되어 저장됨)
}
