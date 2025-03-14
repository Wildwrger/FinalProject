import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { useParams } from 'react-router-dom';
import { Card, CardContent, CardMedia, Typography, Grid, Box, CircularProgress, Alert, Divider } from '@mui/material';
import Comment from '../Comment'; // 댓글 컴포넌트 추가

// 칵테일 재료 DTO 타입 정의
interface CocktailIngDto {
    unit: string;
    amount: number;
    ingredient: string;
    special?: string;  // 특별 재료
}

// 칵테일 상세 정보 DTO 타입 정의 (Flask 응답과 일치하도록 수정)
interface CocktailResDto {
    id: string;
    name: string;
    preparation: string;  // 조리과정
    image: string;
    category: string;
    abv: number;  // 도수
    garnish: string;  // 장식
    glass: string;  // 글래스 타입 (Flask 응답에 포함된 필드)
    like: number;
    report: number;
    author: number;
    ingredients: CocktailIngDto[];
}

const CocktailDetail: React.FC = () => {
    const [cocktail, setCocktail] = useState<CocktailResDto | null>(null);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string>('');
   
    const { id, type } = useParams<{ id: string; type: string }>();

    // 칵테일 정보 불러오기
    useEffect(() => {
        const fetchCocktail = async () => {
            try {
                const response = await axios.get<CocktailResDto>(`http://localhost:8111/test/detail/${id}?type=${type}`);
                console.log('Response Data:', response.data); // 콘솔에 데이터 출력
                setCocktail(response.data);
                setLoading(false);
            } catch (err) {
                setError('칵테일 상세 정보를 불러오는 데 실패했습니다.');
                setLoading(false);
            }
        };

        fetchCocktail();
    }, [id, type]);

    if (loading) return <CircularProgress />;
    if (error) return <Alert severity="error">{error}</Alert>;
    if (!cocktail) return <Alert severity="warning">칵테일을 찾을 수 없습니다.</Alert>;

    return (
        <Box sx={{ maxWidth: 1200, margin: 'auto', padding: 3 }}>
            <Card>
                <CardMedia
                    component="img"
                    image={cocktail.image}
                    alt={cocktail.name}
                    sx={{ borderRadius: 2, height: 800, width: '100%', objectFit: 'cover' }}
                />
                <CardContent>
                    <Typography variant="h3" component="h1" gutterBottom sx={{ fontWeight: 'bold', marginBottom: 3 }}>
                        {cocktail.name}
                    </Typography>
                    <Grid container spacing={2} sx={{ marginBottom: 3 }}>
                        <Grid item xs={12} md={4}>
                            <Typography variant="body1" color="text.secondary">
                                <strong>알콜 도수 (ABV):</strong> {cocktail.abv}%
                            </Typography>
                        </Grid>
                    
                        <Grid item xs={12} md={4}>
                            <Typography variant="body1" color="text.secondary">
                                <strong>글래스:</strong> {cocktail.glass}
                            </Typography>
                        </Grid>


                        <Grid item xs={12} md={4}>
                            <Typography variant="body1" color="text.secondary">
                                <strong>분류:</strong> {cocktail.category}
                            </Typography>
                        </Grid>
                        <Grid item xs={12}>
    <Typography variant="body1" color="text.secondary">
        <strong>조리 과정:</strong>{' '}
        {cocktail.preparation}
    </Typography>
</Grid>

                    </Grid>

                    {/* 재료 */}
                    <Typography variant="h5" component="h2" gutterBottom sx={{ fontWeight: 'bold', marginTop: 3 }}>
                        재료
                    </Typography>
                    <Divider sx={{ marginBottom: 2 }} />
                    <Grid container spacing={2}>
    {cocktail.ingredients?.map((ingredient, index) => (
        <Grid item xs={12} sm={6} md={4} key={index}>
            <Typography variant="body1">
                {ingredient.ingredient === null && ingredient.special ? (
                    `${ingredient.special}`
                ) : (
                    `${ingredient.ingredient}: ${ingredient.amount} ${ingredient.unit}`
                )}
            </Typography>
        </Grid>
    ))}
</Grid>
{cocktail.garnish && (
    <Grid item xs={12} md={6}>
        <Typography variant="body1" color="text.secondary">
            <strong>가니시:</strong> {cocktail.garnish}
        </Typography>
    </Grid>
)}
                    {/* 좋아요, 신고, 작성자 정보 */}
                    <Typography variant="body2" color="text.secondary" sx={{ marginTop: 3 }}>
                        <strong>좋아요:</strong> {cocktail.like} | <strong>신고:</strong> {cocktail.report} | <strong>작성자:</strong> {cocktail.author}
                    </Typography>

                    {/* 댓글 섹션 */}
                    <Comment postId={id ?? ''} />
                </CardContent>
            </Card>
        </Box>
    );
};

export default CocktailDetail;