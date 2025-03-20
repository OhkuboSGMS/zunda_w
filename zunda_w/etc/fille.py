
def increment_file(txt_file_path:str,raise_if_error:bool)->int:
    try:
        with open(txt_file_path, 'r') as f:
            count = int(f.read())
        with open(txt_file_path, 'w') as f:
            f.write(str(count+1))
        return count+1
    except Exception as e:
        if raise_if_error:
            raise e
        return -1