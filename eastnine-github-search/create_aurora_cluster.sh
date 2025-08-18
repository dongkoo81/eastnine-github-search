#!/bin/bash

# Aurora MySQL 클러스터 생성 스크립트
# HLL 테스트용 환경 구축

echo "🚀 Aurora MySQL 클러스터 생성 시작..."

# 설정 변수
CLUSTER_NAME="hll-test-cluster"
VPC_ID="vpc-083e1cd1c3147138a"
SECURITY_GROUP_ID="sg-0ec74c9d52681276f"
PARAMETER_GROUP="aurora-hll-test-params"
INSTANCE_TYPE="db.t3.small"
ENGINE="aurora-mysql"
ENGINE_VERSION="8.0.mysql_aurora.3.06.1"
MASTER_USERNAME="admin"
MASTER_PASSWORD="HllTest123!"

echo "📋 설정 정보:"
echo "  클러스터명: $CLUSTER_NAME"
echo "  VPC ID: $VPC_ID"
echo "  보안 그룹: $SECURITY_GROUP_ID"
echo "  파라미터 그룹: $PARAMETER_GROUP"
echo "  인스턴스 타입: $INSTANCE_TYPE"
echo "  엔진: $ENGINE $ENGINE_VERSION"

# 서브넷 그룹 생성 (필요한 경우)
SUBNET_GROUP_NAME="${CLUSTER_NAME}-subnet-group"

echo "🔧 서브넷 그룹 확인 중..."
if ! aws rds describe-db-subnet-groups --db-subnet-group-name "$SUBNET_GROUP_NAME" >/dev/null 2>&1; then
    echo "📦 서브넷 그룹 생성 중..."
    
    # VPC의 서브넷 목록 조회
    SUBNET_IDS=$(aws ec2 describe-subnets \
        --filters "Name=vpc-id,Values=$VPC_ID" \
        --query 'Subnets[?MapPublicIpOnLaunch==`false`].SubnetId' \
        --output text | tr '\t' ' ')
    
    if [ -z "$SUBNET_IDS" ]; then
        echo "❌ VPC에서 사용 가능한 프라이빗 서브넷을 찾을 수 없습니다."
        exit 1
    fi
    
    # 첫 번째 서브넷 2개만 사용
    SUBNET_ARRAY=($SUBNET_IDS)
    SUBNET_1=${SUBNET_ARRAY[0]}
    SUBNET_2=${SUBNET_ARRAY[1]}
    
    aws rds create-db-subnet-group \
        --db-subnet-group-name "$SUBNET_GROUP_NAME" \
        --db-subnet-group-description "Subnet group for $CLUSTER_NAME" \
        --subnet-ids "$SUBNET_1" "$SUBNET_2"
    
    echo "✅ 서브넷 그룹 생성 완료: $SUBNET_GROUP_NAME"
else
    echo "✅ 서브넷 그룹이 이미 존재합니다: $SUBNET_GROUP_NAME"
fi

# Aurora 클러스터 생성
echo "🗄️ Aurora 클러스터 생성 중..."
aws rds create-db-cluster \
    --db-cluster-identifier "$CLUSTER_NAME" \
    --engine "$ENGINE" \
    --engine-version "$ENGINE_VERSION" \
    --master-username "$MASTER_USERNAME" \
    --master-user-password "$MASTER_PASSWORD" \
    --db-subnet-group-name "$SUBNET_GROUP_NAME" \
    --vpc-security-group-ids "$SECURITY_GROUP_ID" \
    --db-cluster-parameter-group-name "$PARAMETER_GROUP" \
    --backup-retention-period 7 \
    --preferred-backup-window "03:00-04:00" \
    --preferred-maintenance-window "sun:04:00-sun:05:00" \
    --storage-encrypted \
    --deletion-protection

if [ $? -eq 0 ]; then
    echo "✅ Aurora 클러스터 생성 요청 완료"
    echo "⏳ 클러스터 생성 중... (약 10-15분 소요)"
else
    echo "❌ 클러스터 생성 실패"
    exit 1
fi

# 클러스터 상태 확인
echo "🔍 클러스터 상태 확인 중..."
aws rds wait db-cluster-available --db-cluster-identifier "$CLUSTER_NAME"

if [ $? -eq 0 ]; then
    echo "✅ 클러스터가 사용 가능한 상태입니다"
else
    echo "❌ 클러스터 생성 실패 또는 시간 초과"
    exit 1
fi

# Writer 인스턴스 생성
echo "💻 Writer 인스턴스 생성 중..."
aws rds create-db-instance \
    --db-instance-identifier "${CLUSTER_NAME}-writer" \
    --db-cluster-identifier "$CLUSTER_NAME" \
    --engine "$ENGINE" \
    --engine-version "$ENGINE_VERSION" \
    --db-instance-class "$INSTANCE_TYPE" \
    --publicly-accessible \
    --auto-minor-version-upgrade

if [ $? -eq 0 ]; then
    echo "✅ Writer 인스턴스 생성 요청 완료"
else
    echo "❌ Writer 인스턴스 생성 실패"
    exit 1
fi

# Reader 인스턴스 생성
echo "📖 Reader 인스턴스 생성 중..."
aws rds create-db-instance \
    --db-instance-identifier "${CLUSTER_NAME}-reader" \
    --db-cluster-identifier "$CLUSTER_NAME" \
    --engine "$ENGINE" \
    --engine-version "$ENGINE_VERSION" \
    --db-instance-class "$INSTANCE_TYPE" \
    --publicly-accessible \
    --auto-minor-version-upgrade

if [ $? -eq 0 ]; then
    echo "✅ Reader 인스턴스 생성 요청 완료"
else
    echo "❌ Reader 인스턴스 생성 실패"
    exit 1
fi

# 인스턴스 상태 확인
echo "🔍 인스턴스 상태 확인 중..."
aws rds wait db-instance-available --db-instance-identifier "${CLUSTER_NAME}-writer"
aws rds wait db-instance-available --db-instance-identifier "${CLUSTER_NAME}-reader"

if [ $? -eq 0 ]; then
    echo "✅ 모든 인스턴스가 사용 가능한 상태입니다"
else
    echo "❌ 인스턴스 생성 실패 또는 시간 초과"
    exit 1
fi

# 클러스터 정보 출력
echo ""
echo "🎉 Aurora MySQL 클러스터 생성 완료!"
echo ""
echo "📋 클러스터 정보:"
aws rds describe-db-clusters \
    --db-cluster-identifier "$CLUSTER_NAME" \
    --query 'DBClusters[0].[DBClusterIdentifier,Endpoint,ReaderEndpoint,Status]' \
    --output table

echo ""
echo "💻 인스턴스 정보:"
aws rds describe-db-instances \
    --filters "Name=db-cluster-id,Values=$CLUSTER_NAME" \
    --query 'DBInstances[*].[DBInstanceIdentifier,Endpoint.Address,DBInstanceStatus]' \
    --output table

echo ""
echo "🔑 연결 정보:"
echo "  사용자명: $MASTER_USERNAME"
echo "  비밀번호: $MASTER_PASSWORD"
echo ""
echo "📝 다음 단계:"
echo "  1. 보안 그룹에서 MySQL 포트(3306) 접근 허용"
echo "  2. ams_hll_generator.py 스크립트의 연결 정보 업데이트"
echo "  3. HLL 테스트 스크립트 실행"
