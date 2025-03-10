package com.kh.back.repository.auth;


import com.kh.back.entity.member.Member;
import com.kh.back.entity.auth.RefreshToken;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

import java.util.Optional;

@Repository
public interface RefreshTokenRepository extends JpaRepository<RefreshToken, Long> {
    boolean existsByRefreshToken(String refreshToken);
    boolean  existsByMember(Member member);
    Optional<RefreshToken> findByMember(Member member);

    @Transactional
    void deleteByMember(Member member);

}