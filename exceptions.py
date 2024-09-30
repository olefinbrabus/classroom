from fastapi import status, HTTPException

IsNotTeacherException = HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a teacher")

TeaPotException = HTTPException(status_code=status.HTTP_418_IM_A_TEAPOT, detail="im a teapot")