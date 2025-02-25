package com.kh.back.service.redis;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

@Service @RequiredArgsConstructor
@Slf4j
public class RedisService {
	
	private final RedisTemplate<String, Object> redisTemplate;
	
	// Redis에 값 저장
	public void setValue(String key, String value) {
		redisTemplate.opsForValue().set(key, value);
	}
	
	// Redis에서 값 조회
	public String getValue(String key) {
		return (String) redisTemplate.opsForValue().get(key);
	}
	
	// Redis에서 값 삭제
	public void deleteValue(String key) {
		redisTemplate.delete(key);
	}
	
	// 좋아요 수 증가
	public Long incrementLikes(String postId) {
		String key = "likes:" + postId;
		return redisTemplate.opsForValue().increment(key, 1); // 1씩 증가
	}
	
	// 좋아요 수 감소
	public Long decrementLikes(String postId) {
		String key = "likes:" + postId;
		return redisTemplate.opsForValue().decrement(key, 1); // 1씩 감소
	}
	
	// 좋아요 수 조회
	public Long getLikes(String postId) {
		String key = "likes:" + postId;
		String value = (String) redisTemplate.opsForValue().get(key);  // Redis에서 값 가져오기
		log.warn("현재 좋아요 수 : {}", value);
		if (value != null) {
			return Long.parseLong(value);  // 문자열을 Long으로 변환
		}
		return 0L;  // 기본값
	}
	
}

